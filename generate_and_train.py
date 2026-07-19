"""One-command: generate synthetic Delhi data, then train both models."""
from __future__ import annotations

import time

import attribution
import forecaster
from data_pipeline import generate_synthetic_dataset, load_dataset, save_dataset, DATASET_PATH


def main() -> None:
    if DATASET_PATH.exists():
        print(f"[data] Found existing dataset at {DATASET_PATH}; reusing.")
        df = load_dataset()
    else:
        print("[data] Generating synthetic Delhi dataset (90 days × 30 stations)...")
        t0 = time.time()
        df = generate_synthetic_dataset(days=90)
        save_dataset(df)
        print(f"[data] Generated {len(df):,} rows in {time.time()-t0:.1f}s "
              f"→ {DATASET_PATH.name}")

    print(f"\n[Module A] Training AQI forecaster (HistGradientBoosting, horizons=1/24/48/72h)...")
    t0 = time.time()
    forecast_metrics = forecaster.train_all(df)
    print(f"[Module A] Done in {time.time()-t0:.1f}s")

    print(f"\n[Module B] Training source-attribution model (Random Forest)...")
    t0 = time.time()
    attribution.train(df)
    print(f"[Module B] Done in {time.time()-t0:.1f}s")

    print("\n[Module C] Multilingual advisory bot is template-based — no training needed.")
    print("\nAll models saved under artifacts/. Now run:")
    print("    streamlit run app.py")


if __name__ == "__main__":
    main()
