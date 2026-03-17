from pathlib import Path
import pandas as pd

INPUT_CSV = Path("data/raw/metadata/sample_tracks.csv")
OUTPUT_CSV = Path("data/processed/cleaned_metadata.csv")

REQUIRED_COLUMNS = ["track_id", "genre", "file_path"]


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df[REQUIRED_COLUMNS].copy()

    for col in REQUIRED_COLUMNS:
        df[col] = df[col].astype(str).str.strip()

    df = df.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    before_rows = len(df)

    df = df.dropna(subset=["track_id", "genre", "file_path"])
    df = df.drop_duplicates(subset=["track_id"])

    after_rows = len(df)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print("ETL completed successfully.")
    print(f"Rows before cleaning: {before_rows}")
    print(f"Rows after cleaning: {after_rows}")
    print(f"Saved cleaned file to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
