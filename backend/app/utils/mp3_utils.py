"""
Small MP3 helpers used for local audio assembly and diagnostics.

The project runs locally and cannot assume ffmpeg is installed, so the merge
path strips repeated ID3 tags and validates the resulting MP3 stream.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


MPEG1_LAYER3_BITRATES = [
    None,
    32,
    40,
    48,
    56,
    64,
    80,
    96,
    112,
    128,
    160,
    192,
    224,
    256,
    320,
    None,
]

MPEG2_LAYER3_BITRATES = [
    None,
    8,
    16,
    24,
    32,
    40,
    48,
    56,
    64,
    80,
    96,
    112,
    128,
    144,
    160,
    None,
]

SAMPLERATES = {
    "1": [44100, 48000, 32000, None],
    "2": [22050, 24000, 16000, None],
    "2.5": [11025, 12000, 8000, None],
}


def strip_id3v2(data: bytes) -> bytes:
    """Remove leading ID3v2 metadata if present."""
    if len(data) < 10 or not data.startswith(b"ID3"):
        return data
    size_bytes = data[6:10]
    tag_size = (
        ((size_bytes[0] & 0x7F) << 21)
        | ((size_bytes[1] & 0x7F) << 14)
        | ((size_bytes[2] & 0x7F) << 7)
        | (size_bytes[3] & 0x7F)
    )
    return data[10 + tag_size :]


def strip_id3v1(data: bytes) -> bytes:
    """Remove trailing ID3v1 metadata if present."""
    if len(data) >= 128 and data[-128:-125] == b"TAG":
        return data[:-128]
    return data


def _version_name(version_bits: int) -> str | None:
    return {
        0b00: "2.5",
        0b10: "2",
        0b11: "1",
    }.get(version_bits)


def _parse_frame_header(header: bytes) -> dict[str, Any] | None:
    if len(header) < 4:
        return None

    value = int.from_bytes(header, "big")
    if (value >> 21) & 0x7FF != 0x7FF:
        return None

    version_bits = (value >> 19) & 0b11
    layer_bits = (value >> 17) & 0b11
    bitrate_index = (value >> 12) & 0b1111
    samplerate_index = (value >> 10) & 0b11
    padding_bit = (value >> 9) & 0b1

    version = _version_name(version_bits)
    if version is None or layer_bits != 0b01:
        return None

    samplerate = SAMPLERATES[version][samplerate_index]
    if samplerate is None:
        return None

    if version == "1":
        bitrate_kbps = MPEG1_LAYER3_BITRATES[bitrate_index]
        samples_per_frame = 1152
        frame_size = int((144000 * (bitrate_kbps or 0)) / samplerate + padding_bit)
    else:
        bitrate_kbps = MPEG2_LAYER3_BITRATES[bitrate_index]
        samples_per_frame = 576
        frame_size = int((72000 * (bitrate_kbps or 0)) / samplerate + padding_bit)

    if bitrate_kbps is None or frame_size <= 0:
        return None

    return {
        "version": version,
        "samplerate": samplerate,
        "bitrate_kbps": bitrate_kbps,
        "samples_per_frame": samples_per_frame,
        "frame_size": frame_size,
    }


def estimate_mp3_duration_bytes(data: bytes) -> float:
    """Estimate MP3 duration by scanning frame headers."""
    payload = strip_id3v1(strip_id3v2(data))
    if not payload:
        return 0.0

    duration_seconds = 0.0
    index = 0
    payload_length = len(payload)

    while index + 4 <= payload_length:
        header = _parse_frame_header(payload[index : index + 4])
        if header is None:
            index += 1
            continue

        frame_size = header["frame_size"]
        next_index = index + frame_size
        if next_index > payload_length:
            break

        duration_seconds += header["samples_per_frame"] / header["samplerate"]
        index = next_index

    return round(duration_seconds, 3)


def estimate_mp3_duration(path: Path) -> float:
    """Estimate MP3 duration for a local file."""
    if not path.exists() or path.stat().st_size == 0:
        return 0.0
    return estimate_mp3_duration_bytes(path.read_bytes())


def merge_mp3_files(parts: list[Path], output_path: Path) -> tuple[bool, str]:
    """
    Merge MP3 chunks by stripping repeated ID3 tags from every part and
    concatenating the MP3 frame streams in order.
    """
    if not parts:
        return False, "Nenhum chunk de audio foi gerado."

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "wb") as outfile:
            for part in parts:
                if not part.exists() or part.stat().st_size == 0:
                    return False, f"Chunk invalido: {part.name}"

                payload = strip_id3v1(strip_id3v2(part.read_bytes()))
                if not payload:
                    return False, f"Chunk vazio apos remover metadados: {part.name}"
                outfile.write(payload)

        duration = estimate_mp3_duration(output_path)
        if duration <= 0:
            return False, "O MP3 final nao possui frames validos."

        return True, ""
    except Exception as exc:
        return False, str(exc)


def describe_mp3(path: Path) -> dict[str, Any]:
    """Return a small diagnostic payload for logging/status endpoints."""
    return {
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "duration_seconds": estimate_mp3_duration(path) if path.exists() else 0.0,
    }
