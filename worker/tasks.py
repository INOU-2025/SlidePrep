import os
import shutil
import subprocess
from glob import glob

import cv2
from celery.utils.log import get_task_logger

from .celery_app import celery_app
from src.core.app_config_manager import AppConfigManager
from src.core.pipeline_service import PipelineService
from src.steps import StitchingStep

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def process_images_task(self, job_id: str, input_path: str, output_path: str, config_path: str, clean_grid: bool = True):
    """
    Celery task to run the image processing pipeline.
    """
    logger.info(f"Starting job {job_id}")
    self.update_state(state='PROCESSING', meta={'status': 'Initializing pipeline...'})

    try:
        config_manager = AppConfigManager(config_path)
        updated_general = config_manager.general_config.model_copy(
            update={"input_path": input_path, "output_path": output_path}
        )
        config_manager.general_config = updated_general
        service = PipelineService(config=config_manager)
        cfg = service.config
        
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.tif', '*.tiff']
        images = []
        for ext in image_extensions:
            images.extend(glob(os.path.join(input_path, ext)))
            images.extend(glob(os.path.join(input_path, ext.upper())))
            
        if not images:
            raise ValueError(f"No images found in {input_path}")

        logger.info(f"Found {len(images)} images")
        self.update_state(state='PROCESSING', meta={'status': f'Processing {len(images)} images...'})

        # Process images
        processed_count = 0
        total_images = len(images)
        
        # Create a dedicated directory for processed images to avoid overwriting originals
        # and to keep filenames consistent for stitching
        processed_dir = os.path.join(output_path, "processed")
        os.makedirs(processed_dir, exist_ok=True)

        for i, image_path in enumerate(images):
            fname = os.path.basename(image_path)
            # Change extension to .tif for Ashlar compatibility
            name_root, _ = os.path.splitext(fname)
            out_name = f"{name_root}.tif"
            out_path = os.path.join(processed_dir, out_name)
            
            gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if gray is None:
                continue
                
            # Check suffix filter
            suffix_filter = cfg.general_config.suffix_filter
            fname_without_ext = os.path.splitext(fname)[0]
            matches_filter = not suffix_filter or fname_without_ext.endswith(suffix_filter)
            
            should_process = clean_grid and matches_filter

            if should_process:
                def on_step_start(step_name):
                    # Update status with current step
                    current_progress = int((i) / total_images * 80)
                    self.update_state(state='PROCESSING', meta={
                        'progress': current_progress, 
                        'status': f'Processing {i+1}/{total_images}: {step_name}'
                    })

                result = service.run(gray, image_path=image_path, on_step_start=on_step_start)
                output_image = result.image if result is not None else None
                if output_image is None:
                    shutil.copy2(image_path, out_path)
                    continue

                if output_image.ndim == 3:
                    output_image = cv2.cvtColor(output_image, cv2.COLOR_RGB2GRAY)

                cv2.imwrite(out_path, output_image)
            else:
                # Skip preprocessing: Save as Grayscale to matching properties
                # Instead of copy2, we read and write as grayscale to ensure format consistency for Ashlar
                raw_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if raw_gray is not None:
                    cv2.imwrite(out_path, raw_gray)
                else:
                    # Fallback if read fails (unlikely if glob found it)
                    shutil.copy2(image_path, out_path)
            
            processed_count += 1
            progress = int((i + 1) / total_images * 80) # 80% for processing
            self.update_state(state='PROCESSING', meta={'progress': progress, 'status': f'Processed {processed_count}/{total_images}'})

        # Stitching
        self.update_state(state='PROCESSING', meta={'progress': 80, 'status': 'Stitching...'})
        stitching_step = StitchingStep(config=cfg.stitching_config)
        stitched_path = stitching_step.run(processed_dir).data
        
        # Move final result to a known location
        result_dir = os.path.join(output_path, "..", "..", "results")
        dzi_name = f"{job_id}_panorama"
        dzi_output_path = os.path.join(result_dir, dzi_name) # vips adds .dzi extension automatically

        logger.info(f"Generating DZI tiles at {dzi_output_path}.dzi")
        cmd = ["vips", "dzsave", stitched_path, dzi_output_path]
        subprocess.run(cmd, check=True)
        
        final_result_name = f"{dzi_name}.dzi"
        
        logger.info(f"Job {job_id} completed successfully")
        return {'status': 'COMPLETED', 'result_path': final_result_name}

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        raise
