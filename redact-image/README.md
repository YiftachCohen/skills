# redact-image

On-device image redaction for coding agents. Hides sensitive/personal data in a
screenshot or photo **before** the agent reads it, so private pixels never reach
the cloud model.

## How it works

1. **OCR** the image locally with Tesseract to recover text + pixel bounding boxes.
2. **Detect PII** in that text on-device — Microsoft Presidio (spaCy NER +
   pattern recognizers) when installed, with a built-in regex fallback.
3. **Mask** the matching regions (solid box, blur, or pixelate). Optionally mask
   faces with OpenCV.
4. Write a redacted copy + a JSON manifest. The agent then reads **only** the
   redacted copy.

No network calls are made during redaction.

## Quick start

```bash
# install deps (see scripts/requirements.txt for the full story)
pip install Pillow pytesseract
apt-get install tesseract-ocr            # or: brew install tesseract
pip install presidio-analyzer spacy && python -m spacy download en_core_web_lg  # recommended

# redact
python3 scripts/redact.py /path/to/bank-screenshot.png
# -> writes /path/to/bank-screenshot.redacted.png
```

## Example

A bank-statement screenshot with name, email, card number, account number, and
balances — after `redact.py`, the email, card, account number, and every money
amount are blacked out. (Install Presidio to also catch the account holder's
name; regex mode handles only structured data.)

See [`SKILL.md`](./SKILL.md) for the full agent workflow, options, and limitations.

## Files

- `SKILL.md` — instructions the agent loads.
- `scripts/redact.py` — the on-device redaction tool.
- `scripts/requirements.txt` — dependencies.
