"""Shared Matplotlib style for publication-quality figures (Matplotlib only).

White background, subtle grid, Okabe-Ito colourblind-safe palette, 300 dpi.
``save(fig, name)`` writes both a PNG and an SVG into this ``figures/`` folder.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

FIG_DIR = Path(__file__).resolve().parent

# Okabe-Ito colourblind-safe palette.
OKABE_ITO = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "vermillion": "#D55E00",
    "skyblue": "#56B4E9",
    "purple": "#CC79A7",
    "yellow": "#F0E442",
    "black": "#000000",
    "grey": "#999999",
}

# Semantic roles.
US_C = OKABE_ITO["blue"]
UK_C = OKABE_ITO["vermillion"]
EXP_C = OKABE_ITO["skyblue"]
TP_C = OKABE_ITO["orange"]
OBS_C = OKABE_ITO["black"]
OFFICIAL_C = OKABE_ITO["green"]
RESID_C = OKABE_ITO["purple"]


def set_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "axes.grid": True,
        "grid.color": "#cccccc",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.7,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "svg.fonttype": "none",
    })


def save(fig, name: str) -> None:
    """Save ``fig`` as both PNG (300 dpi) and SVG into the figures folder."""
    for ext in ("png", "svg"):
        fig.savefig(FIG_DIR / f"{name}.{ext}")
    plt.close(fig)
    print(f"  saved figures/{name}.png + .svg")
