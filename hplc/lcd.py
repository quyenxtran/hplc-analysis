"""Read calibrated raw Shimadzu detector traces without modifying input."""
import struct
import xml.etree.ElementTree as ET
import numpy as np
import olefile

def read_xml(raw):
    # This instrument writes ASCII XML with some null padding/UTF-16 sections.
    text = raw.replace(b"\x00", b"").decode("latin1")
    return ET.fromstring(text[text.index("<GUD"):text.index("</GUD>") + 6])

def read_float(text):
    return struct.unpack("<d", bytes.fromhex(text))[0]

def decode_chromatogram(raw):
    label, interval_ms, count, total_bytes, _, _ = struct.unpack_from("<6I", raw)
    assert label == 17234 and total_bytes == len(raw)
    position = 24
    values = []
    while len(values) < count:
        size = struct.unpack_from("<H", raw, position)[0]
        position += 2
        payload = raw[position:position + size]
        position += size
        end_size = struct.unpack_from("<H", raw, position)[0]
        position += 2
        assert size == end_size and len(payload) == size
        i, accumulated = 0, 0
        while i < size:
            first = payload[i]
            if first == 0x82:
                i += 1
                continue
            sign = first >> 4
            if sign >= 8:
                raise ValueError("Unsupported delta record")
            width = 1 + sign // 2
            assert i + width <= size
            delta = first & 15
            for byte in payload[i + 1:i + width]:
                delta = delta * 256 + byte
            if sign % 2:
                delta -= 2 ** (8 * width - 4)
            accumulated += delta
            values.append(accumulated)
            i += width
    assert len(values) == count and position == len(raw)
    return np.asarray(values, dtype=np.int64), interval_ms

def read_chromatograms(source):
    """Read acquired detector channels without writing any files."""
    channels = []
    with olefile.OleFileIO(source) as compound:
        metadata = read_xml(compound.openstream(["LSS Raw Data", "2D Data Item"]).read())
        status = compound.openstream(["LSS Raw Data", "Chromatogram Status"]).read()
        detectors = [node for node in metadata.findall("DII") if ".CH#" in node.findtext("DSID", "")]
        for node in detectors:
            channel = int(node.findtext("CN"))
            stream = ["LSS Raw Data", f"Chromatogram Ch{channel}"]
            raw = compound.openstream(stream).read()
            counts, interval = decode_chromatogram(raw)
            record = status[(channel - 1) * 64:channel * 64]
            cf, gain, vf = struct.unpack_from("<3d", record, 16)
            unit = record[40:64].split(b"\x00")[0].decode("ascii")
            assert cf > 0 and vf > 0 and gain == 1
            assert np.isclose(cf, read_float(node.findtext("CF")))
            axis = node.find("./DDI/Axis[@ID='0']")
            selected = axis.find(f"US[@ID='{axis.attrib['DUS']}']")
            assert selected.findtext("Unit") == unit
            assert np.isclose(read_float(selected.findtext("VF")), vf)
            assert int(node.findtext("Rate")) == interval
            start_ms = read_float(node.findtext("DLT"))
            stop_ms = read_float(node.findtext("AT"))
            # Use actual sampling interval, rather than stretching the last point to stop time.
            time = (start_ms + np.arange(len(counts)) * interval) / 60000
            assert time[-1] <= stop_ms / 60000
            wavelength = node.findtext("ADN", "")
            title = "Refractive index" if node.findtext("DSN").startswith("RID") else f"UV at {wavelength.replace('nm', ' nm')}"
            signal = counts * cf / vf
            channels.append({
                "channel": channel, "detector": node.findtext("DSN"), "label": title,
                "wavelength": wavelength or None, "unit": unit, "calibration_factor": cf,
                "value_factor": vf, "gain_factor": gain, "interval_ms": interval,
                "run_stop_min": stop_ms / 60000, "time": time, "counts": counts, "signal": signal,
            })

    assert len(channels) == 3
    assert all(np.array_equal(c["time"], channels[0]["time"]) for c in channels)
    return channels
