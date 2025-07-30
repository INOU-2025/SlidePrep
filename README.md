# 🧬 Microscopy Image Grid Removal and Stitching Pipeline

This project implements a modular image processing pipeline to generate a high-quality Whole Slide Image (WSI) from a collection of microscopy image tiles. Many microscopy systems include a visible grid during tile capture, which can interfere with downstream stitching. This pipeline automatically detects and removes grid lines before reconstructing the full slide using Ashlar.

---

## 📌 Overview

**Pipeline Stages:**
1. **Grayscale Conversion** (if needed)
2. **Image Binarization**
3. **Grid Line Detection**
4. **Grid Mask Generation**
5. **Grid Removal from Tiles**
6. **Whole Slide Image Stitching** (via Ashlar)

Each transformation step is encapsulated as a modular component that can be run individually or chained in a complete pipeline.

---

## 📁 Project Layout

```
project-root/
├── config/                 # Configuration schemas and main config file
├── core/                   # Core pipeline interfaces (PipelineStep, PipelineContext)
├── steps/                  # Individual processing steps (e.g., GridDetectionStep)
├── utils/                  # Drawing, contour analysis, template generation, etc.
├── scripts/                # Scripts for testing individual steps
├── main.py                 # App's main entry point that executes the whole pipeline
├── environment.yml         # Conda environment file
├── requirements.txt        # Pip fallback (if mixing pip packages)
├── README.md               # This file
```

---

## 🔧 Installation

**Recommended**: Use Conda to set up a reproducible environment:

```bash
conda env create -f environment.yml -m <env-name-here>
conda activate <env-name-here>
```

If pip packages are also required:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Full Pipeline *(coming soon)*

A `main.py` script will run the complete pipeline over a directory of microscopy tiles.

---

## 🧪 Running Individual Steps

Each step can be tested in isolation. For example:

```bash
python scripts/run_grid_detection.py \
  --input path/to/tiles \
  --config config/test_grid_detection_config.json
```

This allows for validation of logic, visualization of intermediate results, and fine-tuning of parameters.

---

## ⚙️ Configuration

All processing parameters (thresholds, angles, template sizes, output paths, etc.) are defined in:

```
config/init_config.json
```

Each step reads from a typed configuration class (e.g., `GridDetectionConfig`) to ensure consistency.

---

## 🏗️ Pipeline Design

- **Reusability**: Each `PipelineStep` accepts and updates a shared `PipelineContext`.
- **Debugging**: Integrated logging and visual debugger support.
- **Flexibility**: Steps can operate in pipeline mode or be tested independently via scripts.
- **Future-Proofing**: Easily extendable to support non-image data and other pre/post-processing operations.


---

## 🧠 Credits

Developed by Ivan Rodriguez-Conde @SI6 @ESEI @Universidade de Vigo.

For inquiries, contact: [ivarodriguez@uvigo.gal]()
