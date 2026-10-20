"""Relais de compatibilité vers modele_sans_relief/interface_risque.py."""

from pathlib import Path
import runpy


runpy.run_path(
    str(
        Path(__file__).resolve().parents[1]
        / "modele_sans_relief"
        / "interface_risque.py"
    ),
    run_name="__main__",
)
