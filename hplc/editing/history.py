"""Peak editing: history."""
from dataclasses import asdict
from datetime import datetime, timezone
from .model import json_value

class HistoryOps:
    def _record(self, operation, parameters, before, after):
        self._history.append({"sequence": len(self._history) + 1,
                              "utc_time": datetime.now(timezone.utc).isoformat(),
                              "operation": operation, "parameters": json_value(parameters),
                              "before": [asdict(p) for p in before.values()],
                              "after": [asdict(p) for p in after.values()]})

    def _commit(self, operation, parameters, state):
        self._validate(state)
        before = self.snapshot()
        self._undo.append(before)
        self._redo.clear()
        self._peaks = dict(state)
        self._record(operation, parameters, before, state)

    def undo(self):
        if not self._undo:
            raise ValueError("Nothing to undo.")
        before = self.snapshot()
        self._redo.append(before)
        self._peaks = self._undo.pop()
        self._record("undo", {}, before, self._peaks)

    def redo(self):
        if not self._redo:
            raise ValueError("Nothing to redo.")
        before = self.snapshot()
        self._undo.append(before)
        self._peaks = self._redo.pop()
        self._record("redo", {}, before, self._peaks)

    def execute(self, operation, **parameters):
        allowed = {"insert_peak", "set_baseline", "move_baseline", "reject_peak", "restore_peak",
                   "split_peak", "split_n_peaks", "split_at_valley", "unify_peaks", "set_separation",
                   "skim_peak", "remove_skim", "undo", "redo"}
        if operation not in allowed:
            raise ValueError(f"Unknown editing operation: {operation}")
        try:
            return getattr(self, operation)(**parameters)
        except TypeError as error:
            raise ValueError(f"Invalid arguments for {operation}: {error}") from error
