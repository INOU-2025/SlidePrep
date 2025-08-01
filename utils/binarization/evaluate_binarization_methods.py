#!/usr/bin/env python3
"""
Binarization Method Evaluation Script

Comprehensive evaluation tool for different binarization methods.
Tests multiple binarization approaches on batches of images and generates
detailed statistics and comparative analysis.

This script processes all images in a specified folder, applies different
binarization methods, and provides:
- Success/failure statistics per method
- Pixel distribution analysis
- Output image generation with organized folder structure
- Detailed processing reports

Uses config/test/binarization_test_config.json by default for test-specific settings.
"""

import argparse
import numpy as np
import os
import cv2
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.app_config_manager import AppConfigManager
from core.logger import Logger
from core.debugger import Debugger
from core.context import PipelineContext
from steps.binarization import BinarizationStep
from utils.image_utils import get_supported_image_patterns, filter_images_by_suffix
from glob import glob


def evaluate_binarization_methods(config_path: str):
    """Evaluate different binarization methods on all images in a folder."""
    
    # Initialize basic components first to get config
    cfg = AppConfigManager.get_instance()
    cfg.initialize(config_path)

    # Get input folder from config
    input_folder = cfg.general_config.input_path
    suffix_filter = cfg.general_config.suffix_filter
    
    if not input_folder:
        print("Error: input_path must be specified in the general config section")
        return
    
    if not os.path.exists(input_folder):
        print(f"Error: Input folder not found: {input_folder}")
        return
    
    # Get all supported images from the folder
    image_extensions = get_supported_image_patterns()
    images = []
    for ext in image_extensions:
        images.extend(glob(os.path.join(input_folder, ext)))
        images.extend(glob(os.path.join(input_folder, ext.upper())))
    
    # Apply suffix filter if specified
    images = filter_images_by_suffix(images, suffix_filter)
    if suffix_filter:
        print(f"Applied suffix filter: '{suffix_filter}'")
    
    if not images:
        if suffix_filter:
            print(f"Error: No images found with suffix '{suffix_filter}' in {input_folder}")
        else:
            print(f"Error: No supported images found in {input_folder}")
        print(f"Supported formats: {', '.join(image_extensions)}")
        return
    
    print(f"Found {len(images)} images to process in {input_folder}")
    
    logger = Logger.get_instance()
    logger.initialize(cfg.log_config, enabled=cfg.logger_active, output_dir=cfg.debug_config.output_dir)

    debugger = Debugger.get_instance()
    debugger.initialize(cfg.debug_config, cfg.debug_active)

    # Get output directory from config
    output_base_dir = cfg.general_config.output_path
    if not output_base_dir:
        output_base_dir = cfg.debug_config.output_dir or "debug_output"
    print(f"Output will be saved to: {output_base_dir}")

    # Test the current production method
    methods = [
        {
            "name": "Combined Differential (Production)",
            "config": {
                "threshold_method": "combined_differential"
            }
        }
    ]

    # Create output directories for each method
    method_dirs = {}
    for method in methods:
        method_safe_name = method['name'].replace(" ", "_").replace("(", "").replace(")", "").lower()
        method_dir = os.path.join(output_base_dir, method_safe_name)
        os.makedirs(method_dir, exist_ok=True)
        method_dirs[method_safe_name] = method_dir
        print(f"Created output directory: {method_dir}")

    # Statistics tracking
    total_processed = 0
    method_stats = {method['name']: {'success': 0, 'failed': 0, 'files': []} for method in methods}
    
    # Process each image
    for image_path in images:
        fname = os.path.basename(image_path)
        base_name = os.path.splitext(fname)[0]
        
        # Load the image
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            print(f"⚠️  Could not load image: {fname}")
            continue
            
        print(f"\nProcessing {fname} ({gray.shape[1]}x{gray.shape[0]})")
        total_processed += 1
        
        # Test each method on this image
        for method in methods:
            method_name = method['name']
            method_safe_name = method_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
            
            try:
                # Create config from method settings
                from config.config_schema import BinarizationConfig
                config = BinarizationConfig(**method['config'])
                
                # Create step
                step = BinarizationStep(config, logger=logger, debugger=debugger)
                
                # Create context
                ctx = PipelineContext(
                    input_image=gray.copy(),
                    image_path=image_path, 
                    image_name=f"{fname}_{method_safe_name}",
                    gray_image=gray.copy()
                )
                
                # Run binarization
                step.run(ctx)
                
                if ctx.binarized_image is not None:
                    # Save the binarized result
                    output_filename = f"{base_name}_binarized.png"
                    output_path = os.path.join(method_dirs[method_safe_name], output_filename)
                    
                    cv2.imwrite(output_path, ctx.binarized_image)
                    
                    # Update statistics
                    method_stats[method_name]['success'] += 1
                    method_stats[method_name]['files'].append(output_path)
                    
                    # Calculate pixel statistics
                    white_pixels = np.sum(ctx.binarized_image == 255)
                    total_pixels = ctx.binarized_image.size
                    white_percent = 100 * white_pixels / total_pixels
                    
                    print(f"  ✓ {method_name}: {white_percent:.1f}% white pixels → {output_path}")
                else:
                    method_stats[method_name]['failed'] += 1
                    print(f"  ✗ {method_name}: Failed to create binary image")
                    
            except Exception as e:
                method_stats[method_name]['failed'] += 1
                print(f"  ✗ {method_name}: Error - {e}")
    
    # Print final summary
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_base_dir}")
    print(f"Images processed: {total_processed}")
    print(f"")
    
    for method_name, stats in method_stats.items():
        method_safe_name = method_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
        success_rate = (stats['success'] / total_processed * 100) if total_processed > 0 else 0
        print(f"{method_name}:")
        print(f"  Success: {stats['success']}/{total_processed} ({success_rate:.1f}%)")
        print(f"  Failed: {stats['failed']}")
        print(f"  Output folder: {method_dirs[method_safe_name]}")
        print(f"  Files generated: {len(stats['files'])}")
        print(f"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate binarization methods on a batch of images")
    parser.add_argument("config", nargs="?", default="config/test/binarization_test_config.json", help="Path to test config file")
    args = parser.parse_args()

    evaluate_binarization_methods(args.config)
