#!/usr/bin/env python3
"""Execute versioned Jupyter notebooks in-place and fail on notebook errors."""
from __future__ import annotations

from pathlib import Path
import sys

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOKS = [
    ROOT / "notebooks" / "versions" / "v01_data_validation_riot_scale_2600.ipynb",
    ROOT / "notebooks" / "versions" / "v02_eda_feature_interpretation_riot_scale_2600.ipynb",
    ROOT / "notebooks" / "versions" / "v03_modeling_threshold_riot_scale_2600.ipynb",
    ROOT / "notebooks" / "versions" / "v04_submission_report_riot_scale_2600.ipynb",
]


def execute(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    ep = ExecutePreprocessor(timeout=300, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(ROOT)}})
    nbformat.write(nb, path)
    errors = []
    for idx, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                errors.append((idx, output.get("ename"), output.get("evalue")))
    if errors:
        raise RuntimeError(f"Notebook has execution errors: {path}: {errors[:3]}")


def main(argv: list[str]) -> int:
    notebooks = [Path(arg).resolve() for arg in argv] if argv else DEFAULT_NOTEBOOKS
    for path in notebooks:
        print(f"executing: {path.relative_to(ROOT)}")
        execute(path)
        print(f"complete: {path.relative_to(ROOT)}")
    print("all_notebooks_executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
