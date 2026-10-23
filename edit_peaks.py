"""Run manual editing: python edit_peaks.py --help or --demo."""
from hplc.editing import PeakEditor
from hplc.editing.input import load_editor
from hplc.editing.recipes import apply_recipe
from hplc.editing.plotting import plot_edit_comparison
from hplc.editing.demo import demo_trace_and_recipe
from hplc.editing.runner import run_file
from hplc.editing.cli import main

if __name__ == "__main__":
    main()
