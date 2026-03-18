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
| Storage Account | dsai3202storage |
| Region | East US |
| Redundancy | LRS |
| Containers | `raw` (private), `processed` (private) |

### What Was Uploaded to `raw/`
| Blob | Description |
|------|-------------|
| `fma_small.zip` | Original audio zip, unmodified |
| `fma_metadata.zip` | Original metadata zip, unmodified |
| `_manifest_v1.0.txt` | Ingestion version record |

### How to Run
```bash
python src/ingestion.py
```

### Key Design Decision
Zip files are stored **unextracted** in the raw zone to preserve data 
integrity. Databricks handles extraction at processing time. This follows 
medallion architecture (raw → processed).


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

### Output Files in `processed/`
- `tracks_clean.parquet` — cleaned track metadata
- `features_clean.parquet` — aligned pre-computed feature matrix

### How to Run
```bash
python src/etl.py
```

### Technical Note
FMA metadata CSVs use multi-level headers. The pipeline uses 
`header=[0,1]` when loading and flattens columns into `category_field` 
format (e.g. `track_genre_top`, `set_split`).



## Step 3 — Data Catalog & Governance (Deliverable II.3)

### Data Catalog
See full catalog in [`data_catalog.md`](./data_catalog.md)

### Zone Overview
| Zone | Container | Path | Description |
|------|-----------|------|-------------|
| Raw | raw | fma_small.zip | Original audio zip, unmodified |
| Raw | raw | fma_metadata.zip | Original metadata zip, unmodified |
| Raw | raw | _manifest_v1.0.txt | Ingestion version record |
| Processed | processed | tracks_clean.parquet | Cleaned track metadata |
| Processed | processed | features_clean.parquet | Aligned feature matrix |

### Schema: `tracks_clean.parquet`
| Column | Type | Description | Nullable |
|--------|------|-------------|----------|
| track_id | int (index) | Unique track identifier | No |
| track_genre_top | string | Top-level genre (8 classes) | No |
| track_duration | float | Duration in seconds | No |
| track_title | string | Track title | Yes |
| artist_name | string | Artist name | Yes |
| set_split | string | training / validation / test | No |
| genre_id | int | Numeric encoding of genre label | No |

### Genre Classes (8)
`Electronic` · `Experimental` · `Folk` · `Hip-Hop` · `Instrumental` · 
`International` · `Pop` · `Rock`

### Data Lineage
```
raw/fma_metadata.zip
  -> [ETL: unzip, filter, clean, encode]
  -> processed/tracks_clean.parquet
```



## Step 4 — Exploratory Data Analysis (Deliverable II.4)

EDA was performed in Databricks using `notebooks/01_eda.ipynb`, loading 
data directly from Azure Blob Storage.

### Key Findings
- **Genre distribution:** classes are reasonably balanced across 8 genres
- **Track duration:** majority of tracks fall between 25–35 seconds after cleaning
- **Missing values:** `artist_name` and `track_title` have some nulls; 
  `track_genre_top` has none after ETL
- **MFCC correlation:** adjacent MFCC coefficients show high correlation, 
  confirming timbre captures consistent tonal structure

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

### Output
- `processed/features_extracted.parquet` — 49 features per track

---

## Azure Resources Deployed
| Resource | Type | Purpose |
|----------|------|---------|
| rg-dsai3202-phase1 | Resource Group | Container for all resources |
| dsai3202storage | Storage Account (LRS) | Raw and processed data zones |
| raw | Blob Container | Original unmodified data |
| processed | Blob Container | Cleaned parquet outputs |
| Azure Databricks | Workspace | EDA and feature extraction notebooks |
| Microsoft Purview | Catalog | Data governance and lineage |

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
AZURE_STORAGE_ACCOUNT_NAME=your_account_name
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
