"""Public diagnostic entrypoint for the equity-index pipeline."""

from pipeline.internal.scripts.fetch_equity_indices import main


if __name__ == "__main__":
    main()
