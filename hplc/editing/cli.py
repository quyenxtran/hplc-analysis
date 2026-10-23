"""Batch and demonstration entry points for peak editing."""
import fnmatch
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from ..sorting import natural_key
from . import PeakEditor
from .cli_options import make_parser
from .demo import demo_trace_and_recipe
from .plotting import plot_edit_comparison
from .recipes import apply_recipe
from .runner import run_file

def main():
    parser = make_parser()
    args = parser.parse_args()
    try:
        time, signal, example = demo_trace_and_recipe()
        if args.write_example_recipe:
            if args.write_example_recipe.exists():
                raise ValueError("Recipe file already exists; choose another name to preserve your edits.")
            args.write_example_recipe.write_text(json.dumps(example, indent=2), encoding="utf-8")
            print("Wrote synthetic example recipe; adjust for your trace:", args.write_example_recipe)
            return
        if args.demo:
            if args.source or args.recipe:
                raise ValueError("--demo uses synthetic input and its own recipe; do not supply source/recipe.")
            editor = PeakEditor(time, signal, "Synthetic three-peak example")
            before = apply_recipe(editor, example)
            path = editor.export(args.output, "synthetic_peak_editing")
            (args.output / "synthetic_recipe.json").write_text(json.dumps(example, indent=2), encoding="utf-8")
            for extension in ["svg", "png"]:
                plot_edit_comparison(editor, before, args.output / f"synthetic_comparison.{extension}",
                                     "Synthetic signal | Vertical splits preserve the combined area")
            if args.demo_svg:
                plot_edit_comparison(editor, before, args.demo_svg, "Synthetic signal | Vertical splits preserve the combined area")
            print("Synthetic demonstration areas:", path.resolve())
            return
        if args.demo_svg:
            raise ValueError("--demo-svg requires --demo.")
        if args.source is None or args.recipe is None:
            raise ValueError("Provide a source and --recipe, or use --demo.")
        recipe = json.loads(args.recipe.read_text(encoding="utf-8-sig"))
        if args.source.is_dir():
            sources = sorted((p for p in args.source.iterdir() if p.is_file()
                              and fnmatch.fnmatchcase(p.name.lower(), args.include.lower())
                              and not any(fnmatch.fnmatchcase(p.name.lower(), value.lower()) for value in args.exclude)),
                             key=lambda p: natural_key(p.name))
        else:
            sources = [args.source]
        if not sources:
            raise ValueError("No input files match the requested pattern.")
        report = []
        for source in sources:
            item = {"filename": source.name, "status": "ok", "error": ""}
            try:
                editor, path = run_file(source, recipe, args.output, args.channel, args.time_column, args.signal_column)
                item.update({"active_peak_count": len(editor.peak_table()), "areas_csv": str(path.resolve()),
                             "flagged_peaks": sum(bool(row["flags"]) for row in editor.peak_table())})
            except (OSError, ValueError, AssertionError, struct.error, ET.ParseError) as error:
                item.update(status="error", error=f"{type(error).__name__}: {error}")
            report.append(item)
        args.output.mkdir(parents=True, exist_ok=True)
        manifest = {"recipe": recipe, "recipe_sha256": hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
                    "channel": args.channel, "include": args.include, "exclude": args.exclude, "files": report}
        (args.output / f"editing_manifest_{args.channel}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        failures = sum(row["status"] != "ok" for row in report)
        print(f"Processed {len(report)} input files; {failures} failures. Outputs: {args.output.resolve()}")
        for row in report:
            if row["status"] != "ok":
                print(row["filename"], row["error"])
        if failures:
            raise SystemExit(1)
    except (OSError, ValueError) as error:
        parser.error(str(error))
