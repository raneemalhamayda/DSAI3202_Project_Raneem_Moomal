from pathlib import Path
import pandas as pd
import numpy as np
import librosa

INPUT_CSV = Path("data/raw/metadata/sample_tracks_features.csv")
OUTPUT_CSV = Path("features/mfcc_features.csv")

N_MFCC = 13
TARGET_SR = 22050


def extract_features(audio_path: Path) -> dict:
    y, sr = librosa.load(audio_path, sr=TARGET_SR, mono=True)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y)

    features = {}

    for i in range(N_MFCC):
        features[f"mfcc_{i+1}_mean"] = float(np.mean(mfcc[i]))
        features[f"mfcc_{i+1}_std"] = float(np.std(mfcc[i]))

    features["spectral_centroid_mean"] = float(np.mean(spectral_centroid))
    features["spectral_centroid_std"] = float(np.std(spectral_centroid))
    features["zero_crossing_rate_mean"] = float(np.mean(zcr))
    features["zero_crossing_rate_std"] = float(np.std(zcr))

    return features


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input metadata file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    required_cols = ["track_id", "genre", "file_path"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    rows = []

    for _, row in df.iterrows():
        audio_path = Path(row["file_path"])

        if not audio_path.exists():
            print(f"Skipping missing file: {audio_path}")
            continue

        try:
            feats = extract_features(audio_path)
            feats["track_id"] = row["track_id"]
            feats["genre"] = row["genre"]
            feats["file_path"] = str(audio_path)
            rows.append(feats)
            print(f"Processed: {audio_path}")
        except Exception as e:
            print(f"Failed on {audio_path}: {e}")

    if not rows:
        print("No features extracted.")
        return

    out_df = pd.DataFrame(rows)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_CSV, index=False)

    print(f"Feature extraction completed successfully.")
    print(f"Saved features to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()