# DSAI3202 — Cloud Project: Automatic Music Genre Classification
**Raneem Alhamayda (60300390) | Moomal Gajani (60304437)**

---

## Project Overview
This project builds an end-to-end cloud data pipeline for automatic music genre 
classification using the Free Music Archive (FMA) dataset. We use FMA Small 
(8,000 tracks, 8 genres) as our working dataset, processed entirely on Azure. 
Our hypothesis is that hand-crafted audio features (MFCCs + spectral features) 
fed into a shallow classifier form a strong baseline, which Phase 2 will compare 
against fine-tuned deep audio embeddings (CLAP/VGGish).

---

## Repository Structure
```
DSAI3202-Phase1/
├── README.md
├── requirements.txt
├── data_catalog.md
├── .env                  ← never committed
├── .gitignore
├── src/
│   ├── ingestion.py
│   ├── etl.py
│   └── features.py
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_feature_extraction.ipynb
├── configs/
│   └── pipeline_config.yaml
├── assets/               ← screenshots and figures
└── outputs/
    └── figures/
```

---

## Step 1 — Data Ingestion (Deliverable II.1)

### Dataset
- **Source:** [Official FMA GitHub](https://github.com/mdeff/fma)
- **Files:** `fma_small.zip` (8 GB, 8,000 tracks) and `fma_metadata.zip` (342 MB)
- **Strategy:** FMA Large (93 GB) is stored in Azure Cold Blob tier as a 
  production scale reference. FMA Small is the active working dataset.

### Azure Blob Storage Setup
| Resource | Value |
|----------|-------|
| Resource Group | rg-dsai3202-phase1 |
| Storage Account | dsai3202rm |
| Region | East US |
| Redundancy | LRS |
| Containers | `raw` (private), `processed` (private) |

### What Was Uploaded to `raw/`
| Blob | Description |
|------|-------------|
| `fma_metadata.zip` | Original metadata zip, unmodified |
| `fma_metadata/tracks.csv` | Extracted track metadata |
| `fma_metadata/features.csv` | Extracted pre-computed features |
| `_manifest_v1.0.txt` | Ingestion version record |

### How to Run
```bash
python src/ingestion.py
```

### Key Design Decision
Zip files are stored unextracted in the raw zone to preserve data integrity. 
This follows medallion architecture (raw → processed).

![Raw Container](assets/raw_container_phase1.png)

---

## Step 2 — ETL Pipeline (Deliverable II.2)

### What the Pipeline Does
`src/etl.py` loads the FMA metadata CSVs from blob storage, cleans and 
validates them, then saves parquet files to the `processed` container.

### Cleaning Steps & Justification
| Step | Function | Reason |
|------|----------|--------|
| Filter split | `filter_small_subset()` | Keep only FMA Small (training/validation/test) |
| Drop missing genres | `drop_missing_genres()` | Genre is the target label — cannot be null |
| Remove duplicates | `remove_duplicates()` | Prevent data leakage across splits |
| Standardize duration | `standardize_duration()` | Remove tracks < 5s or > 40s (corrupt/outliers) |
| Encode genre labels | `encode_genre_labels()` | Convert string genres to numeric IDs for ML |

### ETL Output
```
After split filter: 106574 tracks (was 106574)
Dropped 56976 rows with missing genre
Removed 0 duplicate track IDs
Removed 48116 tracks with abnormal duration
Encoded 13 genres: ['Classical', 'Electronic', 'Experimental', 'Folk', 
'Hip-Hop', 'Instrumental', 'International', 'Jazz', 'Old-Time / Historic', 
'Pop', 'Rock', 'Soul-RnB', 'Spoken']
Saved to processed/tracks_clean.parquet
Saved to processed/features_clean.parquet
=== ETL Complete ===
```

### Output Files in `processed/`
- `tracks_clean.parquet` — cleaned track metadata
- `features_clean.parquet` — aligned pre-computed feature matrix

### How to Run
```bash
python src/etl.py
```

### Technical Note
FMA metadata CSVs use multi-level headers. The pipeline uses `header=[0,1]` 
when loading and flattens columns into `category_field` format 
(e.g. `track_genre_top`, `set_split`).

![Processed Container](assets/processed_container_phase1.png)

---

## Step 3 — Data Catalog & Governance (Deliverable II.3)

### Data Catalog
See full catalog in [`data_catalog.md`](./data_catalog.md)

### Zone Overview
| Zone | Container | Path | Description |
|------|-----------|------|-------------|
| Raw | raw | fma_metadata.zip | Original metadata zip, unmodified |
| Raw | raw | fma_metadata/tracks.csv | Extracted track metadata |
| Raw | raw | fma_metadata/features.csv | Extracted features |
| Raw | raw | _manifest_v1.0.txt | Ingestion version record |
| Processed | processed | tracks_clean.parquet | Cleaned track metadata |
| Processed | processed | features_clean.parquet | Aligned feature matrix |

### Schema: `tracks_clean.parquet`
| Column | Type | Description | Nullable |
|--------|------|-------------|----------|
| track_id | int (index) | Unique track identifier | No |
| track_genre_top | string | Top-level genre (13 classes) | No |
| track_duration | float | Duration in seconds | No |
| track_title | string | Track title | Yes |
| artist_name | string | Artist name | Yes |
| set_split | string | training / validation / test | No |
| genre_id | int | Numeric encoding of genre label | No |

### Genre Classes (13)
`Classical` · `Electronic` · `Experimental` · `Folk` · `Hip-Hop` · 
`Instrumental` · `International` · `Jazz` · `Old-Time / Historic` · 
`Pop` · `Rock` · `Soul-RnB` · `Spoken`

### Data Lineage
```
raw/fma_metadata.zip
  -> [ETL: unzip, filter, clean, encode]
  -> processed/tracks_clean.parquet
```

---

## Step 4 — Exploratory Data Analysis (Deliverable II.4)

EDA was performed in Databricks using `notebooks/01_eda.ipynb`, loading 
data directly from Azure Blob Storage.

### Key Findings
- **Genre distribution:** 13 genre classes with varying representation across the dataset
- **Track duration:** majority of tracks fall between 25–35 seconds after cleaning
- **Missing values:** `artist_name` and `track_title` have some nulls; `track_genre_top` has none after ETL
- **MFCC correlation:** adjacent MFCC coefficients show high correlation, confirming timbre captures consistent tonal structure

### Genre Distribution
![Genre Distribution](assets/genre_distribution.png)

### Track Duration Distribution
![Duration Distribution](assets/duration_distribution.png)

### Missing Values by Column
![Missing Values](assets/missing_values.png)

### MFCC Correlation Heatmap
![MFCC Heatmap](assets/mfcc_correlation.png)

---

## Step 5 — Feature Extraction (Deliverable II.5)

Features are extracted in `src/features.py` using `librosa`.

### Feature Justification Table
| Feature | Dimensions | Justification |
|---------|------------|---------------|
| MFCC (mean + std) | 26 | Primary timbre descriptor — most predictive for genre |
| Chroma STFT (mean) | 12 | Captures harmonic and pitch class content |
| Spectral contrast (mean) | 7 | Peak vs valley differences across frequency bands |
| Zero crossing rate | 2 | Proxy for percussiveness and noisiness |
| RMS energy | 2 | Overall loudness and energy profile |
| **Total** | **49** | Hand-crafted baseline for hypothesis testing |

### Why MFCCs over Mel Spectrograms for Phase 1
MFCCs are compact (26 dimensions vs. a full 2D spectrogram) and work 
directly with shallow classifiers without requiring a CNN. They capture 
timbral texture which is the dominant cue for genre. Phase 2 will compare 
this baseline against fine-tuned deep audio embeddings (CLAP or VGGish) 
that operate on full mel spectrograms.

### How to Run
```bash
python src/features.py
```

> **Note:** `fma_small.zip` (8 GB audio) is required to run feature extraction.
> Download from https://github.com/mdeff/fma, upload to the `raw` container,
> then run `python src/features.py`.

---

## Azure Resources Deployed
| Resource | Type | Purpose |
|----------|------|---------|
| rg-dsai3202-phase1 | Resource Group | Container for all resources |
| dsai3202rm | Storage Account (LRS) | Raw and processed data zones |
| raw | Blob Container | Original unmodified data |
| processed | Blob Container | Cleaned parquet outputs |
| Azure Databricks | Workspace | EDA and feature extraction notebooks |

---

## How to Reproduce

### 1. Clone and set up
```bash
git clone https://github.com/YOUR_USERNAME/DSAI3202-Phase1.git
cd DSAI3202-Phase1
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file in the project root:
```
AZURE_STORAGE_CONNECTION_STRING=your_connection_string_here
AZURE_STORAGE_ACCOUNT_NAME=dsai3202rm
```

### 3. Run ingestion
```bash
python src/ingestion.py
```

### 4. Run ETL
```bash
python src/etl.py
```

### 5. Run feature extraction
```bash
python src/features.py
```

### 6. Run EDA
Open `notebooks/01_eda.ipynb` in Databricks and run all cells.

---

## Branch Strategy
All development work is on the `dev` branch, merged to `main` via Pull Request.
```bash
git checkout dev     # active development branch
git checkout main    # stable, submitted version
```

---

## Phase 2 — Modeling, Validation, and Deployment

---

## II.1 — Model Development

### Problem Definition
Multi-class classification across 8 music genres using 49 hand-crafted audio features extracted from real FMA Small audio files using librosa (MFCCs, chroma, spectral contrast, zero-crossing rate, and RMS energy).

### Dataset Used
| Split | Tracks |
|---|---|
| Training | 6,394 |
| Validation | 800 |
| Test | 800 |
| **Total** | **7,994** |

Splits are inherited directly from Phase 1 ETL (`set_split` column) to ensure no data leakage between phases. Features were extracted from the real `fma_small.zip` audio files stored in Azure Blob Storage (`dsai3202projectrm`, `raw` container).

### Feature Extraction
Features were extracted using `extract_features.py` running on Azure ML compute instance `project-compute`, downloading audio directly from the `project_raw` datastore.

| Feature | Dimensions | Justification |
|---|---|---|
| MFCC (mean + std) | 26 | Primary timbre descriptor |
| Chroma STFT (mean) | 12 | Harmonic and pitch class content |
| Spectral contrast (mean) | 7 | Peak vs valley across frequency bands |
| Zero crossing rate (mean + std) | 2 | Proxy for percussiveness |
| RMS energy (mean + std) | 2 | Overall loudness profile |
| **Total** | **49** | |

### Baseline Model — Random Forest
| Parameter | Value |
|---|---|
| n_estimators | 200 |
| random_state | 42 |
| n_jobs | -1 |

**Justification:** Random Forest handles high-dimensional feature spaces well without requiring feature scaling, and provides feature importance scores useful for error analysis.

### Main Model — SVM (RBF Kernel)
| Parameter | Value |
|---|---|
| kernel | rbf |
| C | 10 |
| gamma | scale |
| random_state | 42 |

**Justification:** SVM with RBF kernel is well-suited for non-linear decision boundaries in audio feature spaces.

### Reproducibility
All models use `random_state=42`. Data splits are fixed from Phase 1. Training is fully reproducible by running `python train.py`.

---

## II.2 — Model Validation

### Validation Strategy
- **Primary metric:** Weighted F1-score (accounts for class imbalance)
- **Secondary metrics:** Accuracy, per-class F1, macro F1
- **Validation set** used for model selection; **test set** used only for final evaluation
- No data leakage: splits defined in Phase 1 ETL, not re-randomized
- Each genre has exactly 100 samples in both validation and test sets

### Results

| Model | Val Weighted F1 | Test Weighted F1 | Val Accuracy |
|---|---|---|---|
| Random Forest (baseline) | **0.4981** | **0.4019** | 0.51 |
| SVM (main model) | 0.4666 | — | 0.48 |

**Selected model: Random Forest** (higher validation F1).

### Per-Class Performance (Random Forest, Validation Set)

| Genre | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Hip-Hop | 0.44 | 0.41 | 0.42 | 100 |
| Electronic | 0.60 | 0.55 | 0.58 | 100 |
| Experimental | 0.60 | 0.60 | 0.60 | 100 |
| Folk | 0.56 | 0.67 | 0.61 | 100 |
| Hip-Hop alt | 0.44 | 0.45 | 0.45 | 100 |
| Instrumental | 0.53 | 0.52 | 0.53 | 100 |
| International | 0.19 | 0.15 | 0.17 | 100 |
| Jazz | 0.59 | 0.69 | 0.64 | 100 |

### Error Analysis
- **Best performing genre:** Jazz (F1: 0.64) — very distinct timbral and harmonic profile
- **Second best:** Folk (F1: 0.61) and Experimental (F1: 0.60)
- **Worst performing genre:** International (F1: 0.17) — highly diverse sub-genres make classification difficult with shallow features
- **Key confusion pairs:** Hip-Hop and Electronic share similar percussive MFCC profiles; International gets absorbed into other categories
- **Overall:** Balanced validation set (100 samples/genre) gives reliable per-class estimates

### Improvement vs Metadata Baseline
| Metric | Metadata subset (v1) | Real audio (v2) |
|---|---|---|
| Tracks | 1,482 | 7,994 |
| Val F1 | 0.44 | 0.50 |
| Val samples/genre | Unbalanced (1–41) | Balanced (100 each) |

---

## II.3 — Model Versioning and Registration

| Field | Value |
|---|---|
| Model name | `music-genre-classifier` |
| Version | v2 |
| Algorithm | RandomForestClassifier |
| Training data | `features_real.parquet` (extracted from fma_small audio) |
| Feature set | `mfcc_chroma_spectral_49dim` |
| Val F1 (weighted) | 0.4981 |
| Test F1 (weighted) | 0.4019 |
| Random seed | 42 |
| Workspace | `dsai3202rm` |
| Resource group | `rg-60300390` |

Registration performed via `azureml.core.Model.register()` with all tags logged programmatically in `train.py`.

---

## II.4 — Deployment

> *Completed by Moomal Gajani — see deployment section below*

---

## II.5 — Deployment Validation

> *Completed by Moomal Gajani — see deployment validation section below*

---

## How to Reproduce

### 1. Clone and set up
```bash
git clone https://github.com/YOUR_USERNAME/DSAI3202-Phase2.git
cd DSAI3202-Phase2
pip install -r requirements.txt
```

### 2. Extract features from real audio
```bash
python extract_features.py
```
Downloads `fma_small.zip` from `project_raw` datastore, extracts 49 audio features for all 7,994 tracks, and uploads `features_real.parquet` and `tracks_real.parquet` to `phase1_processed` datastore.

### 3. Run training and registration
```bash
python train.py
```
This will:
- Connect to Azure ML workspace `dsai3202rm`
- Download `features_real.parquet` and `tracks_real.parquet`
- Train Random Forest (baseline) and SVM
- Evaluate both on validation set and select best model
- Save confusion matrix to `outputs/confusion_matrix.png`
- Register the best model as `music-genre-classifier v2` in Azure ML

### Environment
| Library | Purpose |
|---|---|
| scikit-learn | Model training and evaluation |
| librosa | Audio feature extraction |
| pandas / numpy | Data manipulation |
| joblib | Model serialization |
| azureml-core | Azure ML workspace, datastore, model registration |
| matplotlib / seaborn | Confusion matrix visualization |

---

## Azure Resources (Phase 2)

| Resource | Type | Purpose |
|---|---|---|
| `dsai3202rm` | Azure ML Workspace | Model training, registration, deployment |
| `project-compute` | Compute Instance | Training and feature extraction |
| `phase1_processed` | Datastore (Blob, dsai3202rm) | Processed features storage |
| `project_raw` | Datastore (Blob, dsai3202projectrm) | Raw FMA audio files |
| `music-genre-classifier` | Registered Model (v2) | Versioned model artifact |
