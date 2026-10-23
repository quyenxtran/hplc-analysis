"""Batch extraction orchestration."""
from .filters import filter_peaks
from .sorting import natural_key
from .batch_processing import process_file
from .batch_export import finish_export


def extract_folder(folder, output, start=5.0, end=12.0, min_area=1000.0,
                   min_relative_area_percent=1.0, min_retention_time=5.0):
    filter_peaks([], start, end, min_area, min_relative_area_percent, min_retention_time)
    files = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == '.lcd'],
                   key=lambda p: natural_key(p.name))
    if not files:
        raise ValueError('No LCD files found in the input folder.')
    output.mkdir(parents=True, exist_ok=True)
    all_rows, filtered_rows, summaries, manifest = [], [], [], []
    for path in files:
        summary, entry, rows, filtered = process_file(
            path, start, end, min_area, min_relative_area_percent, min_retention_time)
        summaries.append(summary)
        manifest.append(entry)
        all_rows.extend(rows)
        filtered_rows.extend(filtered)
    metadata = finish_export(folder, output, files, summaries, all_rows, filtered_rows,
                             manifest, start, end, min_area, min_relative_area_percent,
                             min_retention_time)
    return summaries, all_rows, metadata
