"""Split markdown knowledge docs into overlapping text chunks."""

from __future__ import annotations

import re


def extract_topic(text: str, fallback: str) -> str:
    match = re.search(r"বিষয়:\s*(\S+)", text)
    if match:
        return match.group(1).strip()
    return fallback


def chunk_text(text: str, *, max_chars: int = 700, overlap: int = 120) -> list[str]:
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    # Prefer splitting on paragraph boundaries
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
        if len(para) <= max_chars:
            buf = para
        else:
            start = 0
            while start < len(para):
                end = min(len(para), start + max_chars)
                chunks.append(para[start:end].strip())
                if end >= len(para):
                    buf = ""
                    break
                start = max(0, end - overlap)
            else:
                buf = ""
    if buf:
        chunks.append(buf)

    # Add soft overlap between consecutive chunks for context
    if overlap > 0 and len(chunks) > 1:
        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{prev_tail}\n{chunks[i]}".strip())
        return [c for c in overlapped if c]

    return chunks
