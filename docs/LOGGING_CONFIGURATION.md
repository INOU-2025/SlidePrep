# Logging Configuration

## 📝 Overview

The SlidePrep pipeline uses a sophisticated logging system following industry standards to provide clear, actionable information at appropriate verbosity levels while maintaining excellent debugging capabilities.

## 🎯 Logging Level Standards

### DEBUG (10) - Development & Troubleshooting
**Use for:** Internal variables, function calls, intermediate results  
**Environment:** Development/testing only

### INFO (20) - Key Process Tracking  
**Use for:** Major checkpoints, user-visible progress, completion status  
**Environment:** Production and development

### WARNING (30) - Recoverable Issues
**Use for:** Unexpected situations, fallback paths, deprecated usage  
**Environment:** All environments

### ERROR (40) - Operation Failures
**Use for:** Individual operation failures, problems users must know about  
**Environment:** All environments

### CRITICAL (50) - Fatal Errors
**Use for:** Fatal errors, missing essentials, unrecoverable failures  
**Environment:** All environments

## ⚙️ Configuration

### Environment-Specific Settings

#### Production Configuration
```json
{
  "log": {
    "log_level": "INFO",
    "log_to_console": true,
    "log_to_file": true,
    "log_file_name": "slideprep_production.log",
    "output_dir": "logs"
  }
}
```

#### Development Configuration  
```json
{
  "log": {
    "log_level": "DEBUG",
    "log_to_console": true,
    "log_to_file": false,
    "output_dir": "logs"
  }
}
```

#### Testing Configuration
```json
{
  "log": {
    "log_level": "WARNING",
    "log_to_console": false,
    "log_to_file": false
  }
}
```

## 📊 Logging Output Examples

### Production (INFO Level)
```
Pipeline initialized with 2 steps
Starting batch processing of 15 images
Grid detection completed: 45 accepted, 3 rejected, 2 uncertain
Batch processing completed: 15/15 images processed successfully
```

### Development (DEBUG Level)  
```
[Binarization] Starting binarization using combined_differential method
Applied suffix filter '_ch00', found 15 matching images  
Loading image: slide_001_ch00.tif
[GridDetection] Starting grid detection on 2048x2048 binary image
[Binarization] Binarization completed successfully
[GridDetection] Grid detection completed: 45 accepted, 3 rejected, 2 uncertain
Successfully processed slide_001_ch00.tif
```

### Error Scenarios
```
ERROR: Could not read corrupted_image.tif
WARNING: No images found in /empty/directory  
CRITICAL: Input folder does not exist: /invalid/path
```

## 🔧 Step-Level Logging

Pipeline steps provide prefixed logging methods:

```python
# In pipeline steps
self.debug("Internal processing details")     # [StepName] message
self.log("Key checkpoint reached")            # [StepName] message  
self.warning("Unexpected situation")          # [StepName] message
self.error("Operation failed")                # [StepName] message
self.critical("Fatal step error")             # [StepName] message
```

## 📈 Logging Benefits

### Development Benefits
- **Detailed tracing**: DEBUG provides step-by-step algorithm progress
- **Clear error context**: Proper error categorization and context
- **Performance insights**: INFO tracks major processing milestones

### Production Benefits  
- **Clean output**: INFO level shows only essential progress
- **Problem identification**: Clear WARNING/ERROR categorization
- **System monitoring**: CRITICAL messages indicate fatal conditions