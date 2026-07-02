#!/usr/bin/env python3
"""
Project setup: install the spaCy English model.

This is the equivalent of:
    python -m spacy download en_core_web_sm

Run once after `uv sync` to prepare the NLP engine used by the pipeline.
"""
import subprocess
import sys


def main() -> None:
    print("Downloading spaCy English model: en_core_web_sm ...")
    cmd = [sys.executable, "-m", "spacy", "download", "en_core_web_sm"]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Failed to install spaCy model.", file=sys.stderr)
        sys.exit(result.returncode)
    print("spaCy model 'en_core_web_sm' is ready.")


if __name__ == "__main__":
    main()
