"""Apply and export a recipe for one input file."""
from pathlib import Path
from .input import load_editor
from .recipes import apply_recipe
from .plotting import plot_edit_comparison

def run_file(source, recipe, output, channel="ri", time_column="time_min", signal_column=None):
    editor = load_editor(source, channel, time_column, signal_column)
    before = apply_recipe(editor, recipe)
    prefix = Path(source).stem + "_" + channel
    area_path = editor.export(output, prefix, source)
    for extension in ["svg", "png"]:
        plot_edit_comparison(editor, before, Path(output) / f"{prefix}_comparison.{extension}")
    return editor, area_path
