"""A synthetic three-component envelope with strongly overlapping peaks."""
import numpy as np
from ..editing import PeakEditor
from .shapes import components


def fitting_demo():
    x = np.linspace(5.5, 8.5, 1501)
    parameters = np.asarray([[0.9, 6.8, 0.18], [0.65, 7.08, 0.17], [0.45, 7.36, 0.2]])
    baseline = 0.08 + 0.02 * (x - 5.5)
    y = baseline + components(x, parameters, "gaussian").sum(axis=0)
    editor = PeakEditor(x, y, "Synthetic overlapping components")
    editor.insert_peak("envelope", 5.8, 8.3, start_mv=0.086, end_mv=0.136)
    return editor, parameters
