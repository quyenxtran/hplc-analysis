"""Auditable edits of a single detector trace in minutes and mV."""
from .state import EditorState
from .validation import ValidationOps
from .history import HistoryOps
from .baselines import BaselineOps
from .endpoints import EndpointOps
from .splitting import SplitOps
from .merging import MergeOps
from .skimming import SkimOps
from .results import ResultOps
from .exporting import ExportOps
from .session import SessionOps


class PeakEditor(EditorState, ValidationOps, HistoryOps, BaselineOps, EndpointOps, SplitOps, MergeOps, SkimOps, ResultOps, ExportOps, SessionOps):
    """Manual area allocation with immutable input, undo/redo, and audit export."""

    def fit_components(self, peak_id, centers_min, model="gaussian", center_tolerance_min=None, starts=5):
        from ..fitting.api import FitOps
        return FitOps.fit_components(self, peak_id, centers_min, model, center_tolerance_min, starts)
