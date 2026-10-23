"""Read exact saved Shimadzu VER1 peak tables; no reintegration."""
import struct
import math
import olefile
from .lcd import read_xml

def parse_peak_table(raw):
    """Decode validated VER1 records, retaining vendor area/height precision."""
    if len(raw) < 20 or raw[:4] != b"VER1":
        raise ValueError("Expected a Shimadzu VER1 peak table with a 20-byte header.")
    count = struct.unpack_from("<I", raw, 4)[0]
    if count == 0:
        # These LCDs reserve one all-zero 792-byte record even for zero peaks.
        if any(raw[20:]):
            raise ValueError("Zero-peak table has unexpected nonzero payload.")
        return []
    record_length, remainder = divmod(len(raw) - 20, count)
    if remainder or record_length < 728:
        raise ValueError("Invalid VER1 peak record length.")
    peaks = []
    for index in range(count):
        offset = 20 + index * record_length
        retention_ms = struct.unpack_from("<I", raw, offset + 4)[0]
        area = struct.unpack_from("<d", raw, offset + 8)[0]
        height = struct.unpack_from("<d", raw, offset + 24)[0]
        start_ms, end_ms = struct.unpack_from("<2I", raw, offset + 56)
        if not math.isfinite(area) or not math.isfinite(height):
            raise ValueError("Peak area or height is not finite.")
        if not start_ms <= retention_ms <= end_ms:
            raise ValueError("Saved retention time lies outside saved peak bounds.")
        peaks.append({
            "peak_number": index + 1,
            "retention_time_min": retention_ms / 60000,
            "area_uV_s": area, "height_uV": height,
            "start_min": start_ms / 60000, "end_min": end_ms / 60000,
        })
    return peaks

def read_saved_peaks(path):
    channels = []
    with olefile.OleFileIO(path) as compound:
        metadata = read_xml(compound.openstream(["LSS Raw Data", "2D Data Item"]).read())
        status = compound.openstream(["LSS Raw Data", "Chromatogram Status"]).read()
        for node in metadata.findall("DII"):
            channel_id = node.findtext("DSID", "")
            if ".CH#" not in channel_id:
                continue
            channel_number = int(node.findtext("CN"))
            record = status[(channel_number - 1) * 64:channel_number * 64]
            display_unit = record[40:64].split(b"\x00")[0].decode("ascii")
            if display_unit != "mV":
                raise ValueError(f"Unsupported display unit {display_unit}; cannot label saved area as uV*s.")
            wavelength = node.findtext("ADN", "")
            if node.findtext("DSN", "").startswith("RID"):
                label, key = "Refractive index", "RI"
            elif wavelength in ("210nm", "254nm"):
                label, key = f"UV at {wavelength}", "UV_" + wavelength
            else:
                raise ValueError(f"Unexpected detector/wavelength: {channel_id} / {wavelength}")
            stream = ["LSS Data Processing", "PT-" + channel_id]
            if not compound.exists(stream):
                peaks, channel_status = [], "no_saved_peak_table"
            else:
                peaks = parse_peak_table(compound.openstream(stream).read())
                channel_status = "ok" if peaks else "no_saved_peaks"
            channels.append({"key": key, "detector": label, "channel_id": channel_id,
                             "stream": "/".join(stream), "status": channel_status, "peaks": peaks})
    if sorted(c["key"] for c in channels) != ["RI", "UV_210nm", "UV_254nm"]:
        raise ValueError("Expected RI, 210 nm, and 254 nm detector channels.")
    return channels
