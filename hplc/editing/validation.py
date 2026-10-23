"""Peak editing: validation."""

class ValidationOps:
    def _validate(self, state):
        roots = sorted((p for p in state.values() if p.enabled and not p.parent_id), key=lambda p: p.start_min)
        for left, right in zip(roots, roots[1:]):
            if left.end_min > right.start_min + 1e-12:
                raise ValueError("Active root peaks overlap. Split one envelope or use a skim to allocate the overlap.")
        for p in state.values():
            self._bounds(p.start_min, p.end_min)
            if p.parent_id:
                parent = state.get(p.parent_id)
                if parent is None or parent.parent_id or not parent.start_min <= p.start_min < p.end_min <= parent.end_min:
                    raise ValueError("A skim must lie inside one existing root peak; nested skims are unsupported.")
                if p.enabled and not parent.enabled:
                    raise ValueError("An active skim needs an active parent.")
        # Rejected skims still reserve their allocation; rejecting does not add
        # their area back to the host. remove_skim explicitly reclaims that area.
        for root in (p for p in state.values() if not p.parent_id):
            children = sorted((p for p in state.values() if p.parent_id == root.peak_id), key=lambda p: p.start_min)
            if any(a.end_min > b.start_min + 1e-12 for a, b in zip(children, children[1:])):
                raise ValueError("Skim windows on the same parent cannot overlap.")

    def _no_skims(self, peak):
        if peak.parent_id or any(p.parent_id == peak.peak_id for p in self._peaks.values()):
            raise ValueError("Remove skim allocations before splitting, unifying, or changing separation.")
