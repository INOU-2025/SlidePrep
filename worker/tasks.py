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
def process_images_task(self, job_id: str, input_path: str, output_path: str, config_path: str):
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
        
        for i, image_path in enumerate(images):
            fname = os.path.basename(image_path)
            gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if gray is None:
                continue
                
            result = service.run(gray, image_path=image_path)
            if result is None:
                continue
                
            # Save intermediate result (similar to main.py)
            output_image = result
            if isinstance(result, tuple):
                output_image = result[0]
                
            if output_image.ndim == 3 and output_image.shape[2] == 3:
                output_image = cv2.cvtColor(output_image, cv2.COLOR_RGB2BGR)
                
            out_name = f"{os.path.splitext(fname)[0]}_processed.jpg"
            out_path = os.path.join(output_path, out_name)
            cv2.imwrite(out_path, output_image)
            
            processed_count += 1
            progress = int((i + 1) / total_images * 80) # 80% for processing
            self.update_state(state='PROCESSING', meta={'progress': progress, 'status': f'Processed {processed_count}/{total_images}'})

        # Stitching
        self.update_state(state='PROCESSING', meta={'progress': 80, 'status': 'Stitching...'})
        stitching_step = StitchingStep(config=cfg.stitching_config)
        stitched_path, _ = stitching_step.run(output_path)
        
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
