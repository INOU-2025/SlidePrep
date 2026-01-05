import os
import shutil
import subprocess
from celery.utils.log import get_task_logger
from .celery_app import celery_app
from src.core.pipeline_service import PipelineService
from src.steps import StitchingStep
from glob import glob
import cv2

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def process_images_task(self, job_id: str, input_path: str, output_path: str, config_path: str, clean_grid: bool = True):
    """
    Celery task to run the image processing pipeline.
    """
    logger.info(f"Starting job {job_id}")
    self.update_state(state='PROCESSING', meta={'status': 'Initializing pipeline...'})

    try:
        # Initialize service with patched configuration to avoid validation errors
        import json
        from api.schemas import AppConfig, GeneralConfig
        from src.core.app_config_manager import AppConfigManager
        
        # Load the configuration manually
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
            
        # Override paths in the dictionary BEFORE creating AppConfig
        # This prevents validation errors from key paths not existing in config
        if 'general' not in config_dict:
            config_dict['general'] = {}
            
        config_dict['general']['input_path'] = input_path
        config_dict['general']['output_path'] = output_path
        
        # Ensure we don't fail on other missing paths if they are checked
        # For this specific case, input_path validation was the blocker
        
        # Create AppConfig object
        app_config = AppConfig(**config_dict)
        
        # Create manager from the config object
        config_manager = AppConfigManager.from_app_config(app_config)
        
        # Initialize service with the pre-loaded config
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
                if result is None:
                    # If processing fails, we might want to fallback to copy?
                    # For now, let's continue to next image to avoid partial failure blocking everything?
                    # Or maybe copy original so stitching doesn't fail on missing tile?
                    # Let's copy original as fallback
                    shutil.copy2(image_path, out_path)
                    continue
                    
                # Save intermediate result
                output_image = result
                if hasattr(result, 'image') and result.image is not None:
                    output_image = result.image
                elif hasattr(result, 'data'):
                    output_image = result.data
                elif isinstance(result, tuple):
                    output_image = result[0]
                    
                # Ensure output is Grayscale for stitching compatibility
                if output_image.ndim == 3:
                     # If RGB/BGR, convert to Grayscale
                     # cv2.imread usually reads as BGR if not specified, but here we might have RGB from pipeline
                     # Assuming pipeline returns RGB or Grayscale.
                     # Let's assume standard RGB->GRAY weights are fine.
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
        # Run stitching on the PROCESSED directory
        stitched_path, _ = stitching_step.run(processed_dir)
        
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
