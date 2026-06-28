# loom-watch

Watch Loom recordings from Claude Code or Codex by turning a Loom URL into a
timestamped transcript/frame manifest.

The bundled `scripts/loom-watch` helper fetches Loom metadata, captions when
available, samples screen frames with `ffmpeg`, and writes:

- `metadata.json`
- `transcript.vtt`
- `transcript.json`
- `frames/*.png`
- `manifest.md`

For Hebrew or other speech where Loom returns empty captions or
`unsupported_language`, run the explicit fallback:

```bash
loom-watch/scripts/loom-watch <loom-url> --openai-transcribe --language he
```

This requires `OPENAI_API_KEY`, extracts audio with `ffmpeg`, and writes an
OpenAI-generated transcript back into the same manifest workflow.

To stay fully local, provide any open-source transcriber command:

```bash
loom-watch/scripts/loom-watch <loom-url> --local-whisper --language he
```

`--local-whisper` auto-detects `whisper-cli` and
`~/.local/share/whisper.cpp/models/ggml-small.bin` when installed. For other
local tools, provide a command:

```bash
loom-watch/scripts/loom-watch <loom-url> \
  --local-transcribe-command 'whisper-cli --no-gpu -m /path/to/model.bin -f {audio} -l {language} -ovtt -of {out_dir}/local-transcript -np' \
  --language he
```

The command can write `{vtt}`, `{json}`, `{txt}`, or print transcript text to
stdout. VTT is preferred because timestamps align best with frames.

Install with:

```bash
npx skills add YiftachCohen/skills --skill loom-watch
```

The workflow uses Loom web endpoints and signed media URLs. They are useful in
practice, but not an official stable Loom API.
