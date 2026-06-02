---
name: redact-image
description: |
  Redact sensitive/personal data from an image ON-DEVICE before the agent reads it, so private pixels never reach the cloud model. Use when the user wants to share a screenshot or photo for its content but hide the private parts — e.g. "read this redacted image", "redact this screenshot before reading it", "obfuscate my personal data in this photo", "hide the account numbers / balances / card number / name in this image", "mask the PII in this bank statement screenshot", "blur the sensitive info then tell me what it says". Trigger on bank/transaction screenshots, invoices, IDs, pay stubs, medical records, or any image where the user says to redact, mask, obfuscate, blur, hide, anonymize, or scrub personal/sensitive/private data before you look at it. The redaction runs locally (OCR + on-device PII detection); the agent then reads only the redacted copy. Do NOT trigger for ordinary image reading where the user has not asked to hide anything.
---

# Redact Image (on-device)

This skill hides sensitive data in an image **on the user's machine, before you
read it**, so the original private pixels are never sent to the model. It works
by OCR-ing the image locally, detecting PII in the recovered text with an
on-device engine, and painting over the matching regions. You then read only the
redacted copy.

The tool is `scripts/redact.py`. It makes **no network calls** — OCR (Tesseract),
PII detection (Presidio/spaCy + regex), and masking (Pillow) all run locally.

## The one rule that makes this private

**Never `Read` the original image. Only ever `Read` the redacted output.**

The entire value of this skill is that sensitive pixels stay on-device. If you
open the original to "see what's there" first, you have already defeated the
purpose. Run the redactor on the file path, then read the `*.redacted.png`.

### A caveat you must tell the user about pasting

If the user *pasted* an image directly into the conversation, it has **already
been uploaded** — redacting it afterward protects nothing. For real protection
the redaction has to happen **before** the image reaches you. So:

- If the image is already pasted, say so plainly: this particular image has
  already left their device, but you can still redact the **file** so future
  shares (or a re-share of the cleaned copy) are safe.
- The protected workflow is: the user gives you a **file path** (or drops the
  file in the repo), you redact it locally, and you read only the result.

## Setup (first run)

The script needs a few local tools. Check and install what's missing:

```bash
# Core (required):
pip install Pillow pytesseract
#   plus the Tesseract engine itself:
#   apt-get install tesseract-ocr   |   brew install tesseract   |   choco install tesseract

# Strongly recommended — enables PERSON / LOCATION name detection:
pip install presidio-analyzer spacy && python -m spacy download en_core_web_lg

# Optional — face redaction (--faces):
pip install opencv-python
```

Without Presidio the script still runs, but in **regex-only** mode it **cannot
detect names or addresses** (only structured data: emails, cards, IBANs, SSNs,
phone numbers, money amounts, long account numbers). If the image contains a
person's name and Presidio isn't installed, you must either install it or mask
the name manually with `--boxes` (see Verify step). Always tell the user which
mode ran — the script prints `Detection engine: presidio` or `regex`.

## Workflow

### 1. Get a file path

Ask the user for the image's path if you don't have one (e.g.
`~/Downloads/statement.png`). Do not open it.

### 2. Run the redactor

```bash
python3 scripts/redact.py /path/to/image.png --manifest /tmp/redaction.json
```

Defaults are tuned for financial/account screenshots (names, emails, phones,
cards, IBANs, SSNs, bank/account numbers, crypto, IPs, locations, and **all
money amounts**). Output is written next to the input as `image.redacted.png`,
and a black solid box is the default mask (the most secure style).

Read the console summary and the manifest — they tell you what was detected
**without revealing the values** (previews are `***`). Note the detection engine.

### 3. Verify the result (do not skip this)

`Read` the **redacted** image and confirm with your own eyes that nothing
sensitive is still legible. OCR is imperfect: it can split a number so an edge
digit leaks, or miss a low-contrast field entirely; and regex mode won't catch
names. This visual check is your safety net.

### 4. Patch any leak, then re-verify

If something sensitive is still visible:

- **A name/location slipped through in regex mode** → install Presidio (step
  Setup) and re-run, or mask it manually.
- **An edge of a field leaked, or OCR missed a region** → mask it by pixel
  coordinates. Estimate the rectangle from the image you just viewed:

  ```bash
  python3 scripts/redact.py /path/to/image.png \
    --boxes "x0,y0,x1,y1; x0,y0,x1,y1" -o /path/to/image.redacted.png
  ```

- **Want more aggressive coverage** → widen the entity set or change the mask
  style (`--style blur` / `--style pixelate`).

Re-read the output and repeat until clean.

### 5. Read the clean copy and answer

Once verified clean, `Read` the redacted image and do whatever the user asked
("tell me what this says", "summarize these transactions", etc.) using only the
redacted version.

## Options reference

| Flag | Purpose |
|---|---|
| `-o, --output PATH` | Where to write the redacted image (default `<name>.redacted.png`). |
| `--style box\|blur\|pixelate` | Mask style. `box` (solid black) is the default and most secure; `blur`/`pixelate` obscure while keeping layout. |
| `--entities LIST` | Comma-separated entity types to redact (overrides the default set). See `--list-entities`. |
| `--faces` | Also detect and mask faces (OpenCV, on-device). |
| `--boxes "x0,y0,x1,y1;..."` | Manually mask extra rectangles — use to patch leaks found during Verify. |
| `--manifest PATH` | Write a JSON report of what was redacted (values are not included). |
| `--min-confidence N` | OCR confidence floor 0–100 (default 0). Kept low on purpose so uncertain words are still redacted rather than left visible. Raise only to cut false positives. |
| `--dry-run` | Report detections without writing an image (useful to preview coverage). |
| `--list-entities` | Print supported entity types. |

Exit codes: `0` redacted image written · `2` nothing sensitive found (a clean
copy is still written) · `3` a dependency is missing · `4` bad input.

## Picking what to redact

The default set is aimed at financial documents and is deliberately broad
(including every money amount). Adjust per request:

| User intent | Suggested flags |
|---|---|
| Bank/transaction screenshot (default) | *(no flags needed)* |
| Hide identity but keep the numbers | `--entities PERSON,EMAIL_ADDRESS,PHONE_NUMBER,LOCATION` |
| Hide account/card numbers but keep names | `--entities CREDIT_CARD,IBAN_CODE,US_BANK_NUMBER,ACCOUNT_NUMBER,US_SSN` |
| Photo of a person / ID with a face | add `--faces` |
| Keep layout readable for context | add `--style blur` or `--style pixelate` |

## Limitations to be honest about

- **Regex mode can't see names.** Only Presidio (spaCy NER) detects PERSON and
  LOCATION. Say which engine ran and recommend installing Presidio when names
  matter.
- **OCR isn't perfect.** Stylized fonts, low contrast, rotated text, or
  handwriting can be missed. The Verify step exists precisely for this — never
  promise a redaction is complete without looking at the output.
- **Only text and (optionally) faces are detected.** Logos, signatures,
  barcodes/QR codes, and handwriting are not auto-detected — mask those with
  `--boxes` if present.
- **The original file is left untouched on disk.** If the user wants it gone,
  they must delete it themselves; don't delete user files unless asked.
