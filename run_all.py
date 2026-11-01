"""Run the whole pipeline:  python run_all.py   (add --force to re-download data)"""
import sys

from src import analysis, build_features, download_data, model

if __name__ == "__main__":
    print("1/4 Downloading data")
    download_data.main()
    print("2/4 Building seasonal tables")
    sys.argv = sys.argv[:1]
    build_features.main()
    print("3/4 Analysis and figures")
    analysis.main()
    print("4/4 Baseline model")
    model.main()
    print("\nAll done. See figures/ and reports/.")
