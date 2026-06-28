---
name: loom-watch
description: |
  Watch, inspect, summarize, or act on Loom recordings by converting a Loom share/embed URL into agent-readable artifacts: metadata, transcript/captions when available, sampled screen frames, and a timestamped manifest. Use this skill whenever the user shares a loom.com/share or loom.com/embed URL, asks you to "watch this Loom", "review this recording", "summarize this video", "extract action items", debug something shown in a Loom, or verify a visual report captured in Loom. Prefer this skill over transcript-only scraping because many useful Looms are screen-only or contain deictic narration like "this" and "that" that requires frame inspection.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - WebFetch
---

# Loom Watch

Convert a Loom video into materials an agent can actually reason about:

- `metadata.json` for title, author, duration, and visibility details.
- `transcript.vtt` and `transcript.json` when Loom exposes captions.
- `openai-transcript.json` when Loom captions are missing and the OpenAI fallback is explicitly enabled.
- `frames/` with timestamped screen captures.
- `manifest.md`, the main reading surface that aligns transcript cues and visual frames.

## Runtime Compatibility

This skill is shared by Claude and Codex. Tool names differ by environment, so map these instructions to the local equivalents:

- Use the local shell tool to run `scripts/loom-watch`.
- Network access may require explicit approval/escalation.
- If browser tools are available and the extractor fails because the video is private, use the browser only to confirm access state; do not try to bypass workspace, SSO, password, or owner-only restrictions.

The extractor relies on Loom's web GraphQL/media endpoints and `ffmpeg`. These are practical but unofficial. If Loom changes endpoint shapes, report that the extractor needs an update instead of inventing unreliable scraping.

## Invoke

Run the bundled script by path while keeping your shell in the active task workspace:

```bash
/path/to/loom-watch/scripts/loom-watch <loom-url>
```

Useful flags:

```bash
/path/to/loom-watch/scripts/loom-watch <loom-url> --fresh
/path/to/loom-watch/scripts/loom-watch <loom-url> --out-dir /tmp/loom-watch
/path/to/loom-watch/scripts/loom-watch <loom-url> --max-frames 60 --interval 4
/path/to/loom-watch/scripts/loom-watch <loom-url> --local-whisper --language he
/path/to/loom-watch/scripts/loom-watch <loom-url> --openai-transcribe --language he
/path/to/loom-watch/scripts/loom-watch <loom-url> --local-transcribe-command 'your-transcriber {audio} > {txt}' --language he
```

Default output lands in `tmp/loom-watch/<video-id>/` under the current working directory. A second run reuses the cached manifest unless `--fresh` is passed.

## Hebrew And Unsupported Loom Captions

Loom may return `unsupported_language` or empty captions for Hebrew speech. When the user needs spoken content from such a video, prefer the local Whisper fallback:

```bash
/path/to/loom-watch/scripts/loom-watch <loom-url> --local-whisper --language he
```

This extracts the audio with `ffmpeg`, runs the installed `whisper-cli` model locally, replaces `transcript.vtt` with timestamped cues when available, and then builds the usual frame-aligned manifest.

Use OpenAI only when local Whisper is unavailable or the local transcript quality is not good enough:

```bash
/path/to/loom-watch/scripts/loom-watch <loom-url> --openai-transcribe --language he
```

With OpenAI, use `--transcription-prompt` when names, product terms, or domain vocabulary matter:

```bash
/path/to/loom-watch/scripts/loom-watch <loom-url> --openai-transcribe --language he --transcription-prompt "מונחים אפשריים: Milgapo, מלגה, סטודנטים"
```

The OpenAI fallback requires `OPENAI_API_KEY`. It is explicit because it may incur API cost. The default model is `whisper-1` because it can return segment timestamps for the manifest.

## Open Source / Local Transcription

If the user does not want API-backed transcription, prefer the installed whisper.cpp shortcut:

```bash
/path/to/loom-watch/scripts/loom-watch <loom-url> --local-whisper --language he
```

`--local-whisper` auto-detects `whisper-cli` and a model in this order: `--local-whisper-model`, `WHISPER_CPP_MODEL`, then `~/.local/share/whisper.cpp/models/ggml-small.bin`. It uses `--no-gpu` by default because Metal/GPU mode can crash on some Homebrew installs; pass `--local-whisper-gpu` only after testing it.

For other local speech-to-text tools, use `--local-transcribe-command`. The skill extracts `audio.wav`, then runs the command and reads one of these outputs:

- `{vtt}` for WebVTT captions, preferred because timestamps are preserved.
- `{json}` for JSON with `segments` or `text`.
- `{txt}` for plain text.
- stdout as a last fallback.

Available placeholders are shell-quoted automatically:

- `{audio}` - extracted audio file.
- `{vtt}` - expected VTT output path.
- `{json}` - expected JSON output path.
- `{txt}` - expected text output path.
- `{out_dir}` - artifact directory.
- `{language}` - language hint such as `he`.

Examples, adjust to the installed tool:

```bash
# whisper.cpp style: write local-transcript.vtt through an output base.
/path/to/loom-watch/scripts/loom-watch <loom-url> \
  --local-transcribe-command 'whisper-cli --no-gpu -m /path/to/ggml-small.bin -f {audio} -l {language} -ovtt -of {out_dir}/local-transcript -np' \
  --language he

# OpenAI Whisper Python CLI style: generate VTT locally, then move it to {vtt}.
/path/to/loom-watch/scripts/loom-watch <loom-url> \
  --local-transcribe-command 'whisper {audio} --language Hebrew --task transcribe --output_format vtt --output_dir {out_dir} && cp {out_dir}/audio.vtt {vtt}' \
  --language he
```

If no local transcriber is installed, say so and offer the OpenAI fallback or install path rather than pretending Loom captions are enough.

## Consumption Protocol

1. Run the extractor and wait for it to print the `manifest.md` path.
2. Read `manifest.md` first. It is the index and should usually be enough to understand the video structure.
3. Read `transcript.vtt` only if you need exact caption wording beyond the manifest.
4. Open frames selectively. Focus on frames around important transcript cues, visual-only changes, errors, code, forms, settings, or UI states the user cares about.
5. If a frame contains small text, crop and upscale the relevant region before drawing conclusions:

```bash
ffmpeg -i frames/frame_000_0000.00.png -vf "crop=W:H:X:Y,scale=iw*2:ih*2" /tmp/loom-crop.png
```

Do not guess from the transcript when the screen contains the answer. Phrases like "this button", "that value", "here", or "it looks like this" are visual references; inspect the aligned frame.

## What To Report

Adapt the output to the user's ask:

- For summaries: give the title, duration, high-signal summary, and timestamped action items.
- For bug reports: identify the visible repro path, expected vs actual behavior, timestamps/frames used as evidence, and missing information.
- For code or UI reviews: cite the timestamp and frame file for each visual claim.
- For transcript extraction: provide the transcript with timestamps, and say when captions are empty or unavailable.

If the Loom has no captions, say so plainly and base the answer on frames. If the frames are insufficient because the video is too fast, blurry, cropped, or private, ask for a clearer recording or access change.

## Privacy And Access Boundaries

Only process Looms the user provided or has permission to review. Public or unlisted links are usually accessible. Private videos behind SSO, passwords, or workspace restrictions may fail; ask the user to share an accessible link or provide the relevant transcript/screenshots.

Do not include signed CDN URLs in the final answer. They are temporary implementation details and may reveal access tokens.

## Failure Handling

- Exit code `2`: invalid URL or unsupported arguments.
- Exit code `3`: Loom metadata/transcript lookup failed.
- Exit code `4`: transcript/caption download failed.
- Exit code `5`: video URL was unavailable.
- Exit code `6`: `ffmpeg` failed or is missing.

When the extractor fails, report the precise stage and the likely remedy. For example: "The Loom is private/password-protected; please change sharing to anyone with the link" or "ffmpeg is not installed in this environment."
