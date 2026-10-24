#!/usr/bin/env python3
"""Compatibility entry point for the bundled OntoLink project installer."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'skills/ontolink-skills/scripts/project_setup.py'), run_name='__main__')
