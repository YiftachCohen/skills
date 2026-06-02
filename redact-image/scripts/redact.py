#!/usr/bin/env python3
"""
On-device image redaction for sensitive screenshots and photos.

Pipeline (runs entirely locally — no network calls):
  1. OCR the image with Tesseract to get words + pixel bounding boxes.
  2. Detect PII in the recovered text using Microsoft Presidio (spaCy NER +
     pattern recognizers) when available, falling back to built-in regex
     recognizers otherwise.
  3. Mask the pixels behind every detected span (solid box, blur, or pixelate).
  4. Optionally mask detected faces with OpenCV.
  5. Write a redacted copy plus a JSON manifest describing what was hidden.

The original image is never modified and never sent anywhere. Only the
redacted copy is intended to be handed to a cloud model.

Usage:
  python3 redact.py INPUT [-o OUTPUT] [--style box|blur|pixelate]
                    [--entities LIST] [--faces] [--manifest PATH]
                    [--min-confidence FLOAT] [--dry-run] [--list-entities]

Exit codes:
  0  success (redacted image written, or dry-run completed)
  2  no sensitive content detected (image copied through unchanged)
  3  a required dependency is missing
  4  bad input (file not found / unreadable)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Default entity set. Tuned for financial / account screenshots, which is the
# most common case (bank statements, transaction lists, invoices).
# ---------------------------------------------------------------------------
DEFAULT_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_SSN",
    "US_BANK_NUMBER",
    "CRYPTO",
    "IP_ADDRESS",
    "LOCATION",
    "MONEY",            # custom recognizer (see below)
    "ACCOUNT_NUMBER",   # custom recognizer
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Word:
    text: str
    left: int
    top: int
    width: int
    height: int
    start: int          # char offset of this word in the reconstructed text
    end: int            # exclusive

    @property
    def box(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.left + self.width, self.top + self.height)


@dataclass
class Detection:
    label: str
    start: int
    end: int
    text: str
    score: float = 1.0
    boxes: list[tuple[int, int, int, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1: OCR
# ---------------------------------------------------------------------------
def run_ocr(image, min_confidence: float) -> tuple[str, list[Word]]:
    """Return (reconstructed_text, words). Words carry pixel boxes + char offsets."""
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        fail(
            "pytesseract is not installed.\n"
            "  Install with: pip install pytesseract\n"
            "  And the engine: apt-get install tesseract-ocr  (or: brew install tesseract)",
            code=3,
        )

    try:
        data = pytesseract.image_to_data(image, output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError:
        fail(
            "The Tesseract OCR engine is not installed (the Python wrapper is, "
            "but the binary is missing).\n"
            "  apt-get install tesseract-ocr   # Debian/Ubuntu\n"
            "  brew install tesseract           # macOS\n"
            "  choco install tesseract          # Windows",
            code=3,
        )

    words: list[Word] = []
    pieces: list[str] = []
    cursor = 0
    last_line_key = None

    n = len(data["text"])
    for i in range(n):
        text = data["text"][i]
        if not text or not text.strip():
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        # Tesseract reports -1 for non-word rows; keep words above threshold.
        if conf >= 0 and conf < min_confidence:
            continue

        line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if last_line_key is not None and line_key != last_line_key:
            pieces.append("\n")
            cursor += 1
        elif pieces:
            pieces.append(" ")
            cursor += 1
        last_line_key = line_key

        start = cursor
        pieces.append(text)
        cursor += len(text)
        words.append(
            Word(
                text=text,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
                start=start,
                end=cursor,
            )
        )

    return "".join(pieces), words


# ---------------------------------------------------------------------------
# Step 2: PII detection
# ---------------------------------------------------------------------------
def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for idx, d in enumerate(digits):
        if idx % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


# Regex fallback recognizers. Used when Presidio is unavailable, and always
# used for MONEY / ACCOUNT_NUMBER which Presidio does not cover out of the box.
REGEX_RECOGNIZERS: list[tuple[str, re.Pattern]] = [
    ("EMAIL_ADDRESS", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE_NUMBER", re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}(?!\d)")),
    ("US_SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("IBAN_CODE", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,3})?\b")),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    # Money: currency symbol or code adjacent to an amount, or a bare amount
    # with thousands/decimal formatting that looks monetary.
    ("MONEY", re.compile(
        r"(?:[$£€¥₪₹]\s?\d[\d,]*(?:\.\d{1,2})?)"
        r"|(?:\b\d[\d,]*\.\d{2}\b)"
        r"|(?:\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|ILS|NIS|JPY|INR|CHF|CAD|AUD)\b)"
    )),
]

# Credit cards and long account numbers are validated separately so we can
# apply Luhn / length heuristics and cut false positives.
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
ACCOUNT_RE = re.compile(r"\b\d[\d -]{6,}\d\b")


def detect_regex(text: str, entities: set[str]) -> list[Detection]:
    found: list[Detection] = []

    for label, pattern in REGEX_RECOGNIZERS:
        if label not in entities:
            continue
        for m in pattern.finditer(text):
            found.append(Detection(label, m.start(), m.end(), m.group(), 0.6))

    if "CREDIT_CARD" in entities:
        for m in CARD_RE.finditer(text):
            if luhn_ok(m.group()):
                found.append(Detection("CREDIT_CARD", m.start(), m.end(), m.group(), 0.9))

    if "ACCOUNT_NUMBER" in entities:
        for m in ACCOUNT_RE.finditer(text):
            digit_count = sum(c.isdigit() for c in m.group())
            if 8 <= digit_count <= 20:
                found.append(Detection("ACCOUNT_NUMBER", m.start(), m.end(), m.group(), 0.5))

    return found


def detect_presidio(text: str, entities: set[str]) -> list[Detection] | None:
    """Return Presidio detections, or None if Presidio is unavailable."""
    try:
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    except ImportError:
        return None

    try:
        analyzer = AnalyzerEngine()
    except Exception as exc:  # spaCy model missing, etc.
        warn(f"Presidio could not start ({exc}); using regex recognizers only.")
        return None

    # Add custom recognizers Presidio lacks: MONEY and ACCOUNT_NUMBER.
    money_patterns = [
        Pattern("currency_symbol", r"[$£€¥₪₹]\s?\d[\d,]*(?:\.\d{1,2})?", 0.6),
        Pattern("decimal_amount", r"\b\d[\d,]*\.\d{2}\b", 0.4),
        Pattern("currency_code", r"\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|ILS|NIS|JPY|INR|CHF|CAD|AUD)\b", 0.6),
    ]
    analyzer.registry.add_recognizer(
        PatternRecognizer(supported_entity="MONEY", patterns=money_patterns)
    )
    analyzer.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="ACCOUNT_NUMBER",
            patterns=[Pattern("long_digits", r"\b\d[\d -]{6,}\d\b", 0.4)],
        )
    )

    requested = [e for e in entities] or None
    results = analyzer.analyze(text=text, entities=requested, language="en")
    return [
        Detection(r.entity_type, r.start, r.end, text[r.start:r.end], float(r.score))
        for r in results
    ]


# ---------------------------------------------------------------------------
# Step 3: Map detections to word boxes
# ---------------------------------------------------------------------------
def attach_boxes(detections: Iterable[Detection], words: list[Word]) -> list[Detection]:
    kept: list[Detection] = []
    for det in detections:
        boxes = [
            w.box for w in words
            if w.start < det.end and w.end > det.start  # span overlap
        ]
        if boxes:
            det.boxes = boxes
            kept.append(det)
    return kept


# ---------------------------------------------------------------------------
# Step 4: Apply redaction
# ---------------------------------------------------------------------------
def apply_redaction(image, detections: list[Detection], style: str, pad: int = 2):
    from PIL import ImageDraw, ImageFilter

    img = image.convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    for det in detections:
        for (x0, y0, x1, y1) in det.boxes:
            x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
            x1 = min(w, x1 + pad); y1 = min(h, y1 + pad)
            if x1 <= x0 or y1 <= y0:
                continue
            if style == "box":
                draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
            elif style == "blur":
                region = img.crop((x0, y0, x1, y1))
                radius = max(8, (x1 - x0) // 4)
                img.paste(region.filter(ImageFilter.GaussianBlur(radius)), (x0, y0))
            elif style == "pixelate":
                region = img.crop((x0, y0, x1, y1))
                small = region.resize((max(1, (x1 - x0) // 12), max(1, (y1 - y0) // 12)))
                img.paste(small.resize(region.size), (x0, y0))
    return img


def redact_faces(image, detections: list[Detection], style: str):
    """Append face detections (OpenCV Haar cascade, fully on-device)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        warn("--faces requested but opencv-python is not installed; skipping face redaction.")
        return detections

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    for (x, y, fw, fh) in faces:
        detections.append(
            Detection("FACE", -1, -1, "<face>", 0.8, boxes=[(int(x), int(y), int(x + fw), int(y + fh))])
        )
    return detections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def fail(msg: str, code: int) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def dedupe(detections: list[Detection]) -> list[Detection]:
    """Drop detections fully contained within a higher-scoring overlapping one."""
    detections = sorted(detections, key=lambda d: (-(d.end - d.start), -d.score))
    kept: list[Detection] = []
    for det in detections:
        if det.start < 0:  # faces have no char span
            kept.append(det)
            continue
        covered = any(
            k.start <= det.start and k.end >= det.end and k.label == det.label
            for k in kept if k.start >= 0
        )
        if not covered:
            kept.append(det)
    return kept


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Redact sensitive content in an image on-device.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="path to the image to redact")
    parser.add_argument("-o", "--output", help="output path (default: <name>.redacted.png)")
    parser.add_argument("--style", choices=["box", "blur", "pixelate"], default="box",
                        help="how to mask matches (default: box = solid, most secure)")
    parser.add_argument("--entities", help="comma-separated entity types to redact "
                        "(default: the financial-document set; use --list-entities to see all)")
    parser.add_argument("--faces", action="store_true", help="also redact detected faces (OpenCV)")
    parser.add_argument("--boxes", help="manually mask extra pixel rectangles to patch any leak "
                        "spotted on the output. Format: 'x0,y0,x1,y1;x0,y0,x1,y1' "
                        "(coordinates in the input image's pixel space)")
    parser.add_argument("--manifest", help="write a JSON report of redactions to this path")
    parser.add_argument("--min-confidence", type=float, default=0.0,
                        help="minimum OCR word confidence 0-100 (default: 0). Kept low on "
                        "purpose: discarding low-confidence words could leave a sensitive "
                        "number visible but un-redacted. Raise it only to cut false positives.")
    parser.add_argument("--dry-run", action="store_true",
                        help="detect and report but do not write a redacted image")
    parser.add_argument("--list-entities", action="store_true", help="print supported entities and exit")
    args = parser.parse_args(argv)

    if args.list_entities:
        print("Supported entity types:")
        for e in DEFAULT_ENTITIES + ["DATE_TIME", "URL", "NRP", "MEDICAL_LICENSE", "FACE (via --faces)"]:
            print(f"  {e}")
        print("\nThe default set is the financial-document list above (minus FACE).")
        return 0

    if not args.input:
        parser.error("the input image path is required")

    in_path = Path(args.input)
    if not in_path.is_file():
        fail(f"input file not found: {in_path}", code=4)

    try:
        from PIL import Image
    except ImportError:
        fail("Pillow is not installed. Install with: pip install Pillow", code=3)

    try:
        image = Image.open(in_path)
        image.load()
    except Exception as exc:
        fail(f"could not read image: {exc}", code=4)

    entities = set(
        e.strip() for e in args.entities.split(",")
    ) if args.entities else set(DEFAULT_ENTITIES)

    # ---- detect ----
    text, words = run_ocr(image, args.min_confidence)

    detections = detect_presidio(text, entities)
    engine = "presidio"
    if detections is None:
        warn("Presidio not available; using built-in regex recognizers "
             "(install presidio-analyzer + spaCy for stronger detection).")
        detections = detect_regex(text, entities)
        engine = "regex"
    else:
        # Presidio doesn't ship MONEY/ACCOUNT regexes identically; union for safety.
        have = {d.label for d in detections}
        for label in ("MONEY", "ACCOUNT_NUMBER"):
            if label in entities and label not in have:
                detections += detect_regex(text, {label})

    detections = attach_boxes(detections, words)
    detections = dedupe(detections)

    if args.faces:
        detections = redact_faces(image, detections, args.style)

    if args.boxes:
        for chunk in args.boxes.split(";"):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                x0, y0, x1, y1 = (int(float(v)) for v in chunk.split(","))
            except ValueError:
                fail(f"--boxes entry is not 'x0,y0,x1,y1': {chunk!r}", code=4)
            detections.append(
                Detection("MANUAL", -1, -1, "<manual>", 1.0,
                          boxes=[(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))])
            )

    # ---- report ----
    summary: dict[str, int] = {}
    for d in detections:
        summary[d.label] = summary.get(d.label, 0) + 1

    print(f"Detection engine: {engine}")
    print(f"OCR recovered {len(words)} words.")
    if not detections:
        print("No sensitive content detected.")
    else:
        print(f"Found {len(detections)} item(s) to redact:")
        for label, count in sorted(summary.items()):
            print(f"  {label}: {count}")

    if args.manifest:
        manifest = {
            "input": str(in_path),
            "engine": engine,
            "entities_requested": sorted(entities),
            "summary": summary,
            "detections": [
                {"label": d.label, "score": round(d.score, 3),
                 "boxes": d.boxes, "preview": ("<face>" if d.start < 0 else "***")}
                for d in detections
            ],
        }
        Path(args.manifest).write_text(json.dumps(manifest, indent=2))
        print(f"Manifest written to {args.manifest}")

    if args.dry_run:
        return 0 if detections else 2

    if not detections:
        # Nothing to hide: still produce an output so callers have one path to read.
        out_path = Path(args.output) if args.output else in_path.with_suffix(".redacted.png")
        image.convert("RGB").save(out_path)
        print(f"No redactions needed; clean copy written to {out_path}")
        return 2

    redacted = apply_redaction(image, detections, args.style)
    out_path = Path(args.output) if args.output else in_path.with_suffix(".redacted.png")
    redacted.save(out_path)
    print(f"Redacted image written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
