"""Compatibility entry point for bundled installation regression tests."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'skills/ontolink-skills/scripts/test_project_setup.py'), run_name='__main__')
