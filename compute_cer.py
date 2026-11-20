#!/usr/bin/env python3
"""CLI entry point; all normalization is configured in rules/*.yaml."""
from pipeline import main, load_records, score

if __name__ == '__main__':
    main()
