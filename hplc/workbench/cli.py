"""Launch a local browser editor with an LCD/CSV file, folder, or synthetic demo."""
import argparse
from pathlib import Path
import webbrowser
from .state import Workbench
from .server import make_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--channel", choices=["ri", "uv210", "uv254"], default="ri")
    parser.add_argument("--output", type=Path, default=Path("editing_results/workbench"))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--audit", type=Path, help="Resume saved manual edits against the selected trace")
    args = parser.parse_args()
    try:
        workbench = Workbench(args.source, args.channel, args.output)
        if args.audit:
            from ..editing import PeakEditor
            workbench.editor = PeakEditor.from_audit(workbench.editor.time_min, workbench.editor.signal_mv, args.audit)
        server, token = make_server(workbench, args.port)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    url = f"http://127.0.0.1:{server.server_port}/#{token}"
    print("Local HPLC editor:", url, flush=True)
    print("Close with Ctrl+C. Export before closing or changing files.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
