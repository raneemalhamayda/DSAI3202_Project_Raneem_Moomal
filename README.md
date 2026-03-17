# DSAI3202_Project_Raneem_Moomal
Phase 1 project for automatic music genre classification using the FMA dataset, including ingestion, ETL, EDA, feature extraction, and Azure deployment.
# Automatic Music Genre Classification for Playlist Organization using FMA

## Project Description
This project builds an AI system that ingests audio tracks and predicts music genre labels to support playlist organization and search.

## Hypothesis
A pre-trained audio embedding model fine-tuned on the FMA dataset will achieve higher macro-F1 for genre classification than a baseline model built using hand-crafted audio features such as MFCCs with a shallow classifier.

## Dataset
The project uses the FMA dataset, including audio files and metadata files for genre labeling.

## Ingestion Plan
The dataset will be ingested in batch mode. Raw audio and metadata files will be stored separately and preserved without modification.

## ETL Pipeline
The ETL process will load metadata, clean missing or invalid records, map track IDs to audio file paths, and generate a processed manifest for training and evaluation.

## EDA
Exploratory data analysis will summarize class distribution, missing data, and sample audio representations such as waveforms or spectrograms.

## Feature Extraction
Two feature approaches will be prepared:
1. Hand-crafted features such as MFCCs, spectral centroid, and zero-crossing rate
2. Pre-trained audio embeddings

## Azure Setup
Azure Storage and Azure Machine Learning will be used to store and process project artifacts.

## Team Roles
Raneem: repository setup, ingestion, manifest creation, Azure setup, and documentation  
Moomal: ETL, validation, EDA, and feature extraction

## How to Run
Instructions will be added after the pipeline scripts are finalized.
