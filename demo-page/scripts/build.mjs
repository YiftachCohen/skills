#!/usr/bin/env node
// Build a demo page into one self-contained HTML file.
//
//   node build.mjs <page.html> [-o <out.html>] [--check]
//
// - Fills <style data-journal></style> with assets/journal.css.
// - For every data-figure="<name>" in the page, bundles figures/<name>.tsx
//   (next to the page; default export = a React component) with stageshow's
//   own esbuild and React, mounts it into each matching element, and inlines
//   the JS and CSS.
// - Writes <out>.html (an Artifact-ready fragment: no <html>/<head>/<body>)
//   and <out>.preview.html (a full document for a local browser).
//
// - Renders every <pre data-mermaid>…</pre> to a static SVG in the Journal
//   theme (assets/mermaid-theme.json), using Chrome and the Mermaid script
//   from jsDelivr at build time. The page ships the SVG, not Mermaid.
//
// - With --check, also writes what the comprehension check reads, so the
//   reader never has to drive a browser: <out>.txt (the page's text in reading
//   order, details opened, each diagram's title inline) and
//   <out>.first-screen.png (1280x900, figures at their final still).
//
// Never open the built .html files: the inlined bundle makes them very large.
// Everything the agent needs is in the paths printed.
//
// Figures import the kit as 'stageshow/kit' and the look as 'demo-page/figure/look'.
// Stageshow (and its playwright-core, for Mermaid) is found at $STAGESHOW_DIR or
// the usual skills folders.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { homedir } from 'node:os'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const SKILL = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const args = process.argv.slice(2)
const page = args.find((a, i) => !a.startsWith('-') && args[i - 1] !== '-o')
if (!page) {
  console.error('usage: node build.mjs <page.html> [-o <out.html>]')
  process.exit(2)
}
const pagePath = resolve(page)
const outArg = args.includes('-o') ? args[args.indexOf('-o') + 1] : join(dirname(pagePath), 'dist', basename(pagePath))
const out = resolve(outArg).replace(/\.html$/, '')

let html = readFileSync(pagePath, 'utf8')
if (!html.includes('<style data-journal></style>')) {
  console.error('page has no <style data-journal></style>; copy the head from examples/search-rollout/page.html')
  process.exit(1)
}
html = html.replace('<style data-journal></style>', () => `<style>\n${readFileSync(join(SKILL, 'assets/journal.css'), 'utf8')}</style>`)

const MERMAID = 'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js'
const sources = [...html.matchAll(/<pre data-mermaid>([\s\S]*?)<\/pre>/g)]
if (sources.length) {
  const decode = (t) => t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&')
  const { chromium } = createRequire(join(findStageshow(), 'package.json'))('playwright-core')
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' })
  try {
    const tab = await browser.newPage()
    // Mermaid measures labels as it lays out, so the fonts must be loaded first
    const fonts = html.match(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/)?.[0] ?? ''
    await tab.setContent(`<!doctype html><html><head>${fonts}</head><body><span style="font-family:'Hanken Grotesk';font-weight:400">a</span><span style="font-family:'Hanken Grotesk';font-weight:600">a</span></body></html>`)
    await tab.addScriptTag({ url: MERMAID })
    await tab.evaluate(() => document.fonts.ready)
    const config = JSON.parse(readFileSync(join(SKILL, 'assets/mermaid-theme.json'), 'utf8'))
    const svgs = await tab.evaluate(async ({ codes, config }) => {
      window.mermaid.initialize(config)
      const out = []
      for (const [i, code] of codes.entries()) {
        try {
          out.push({ svg: (await window.mermaid.render(`mermaid-${i}`, code)).svg })
        } catch (e) {
          out.push({ error: String(e?.message ?? e) })
        }
      }
      return out
    }, { codes: sources.map((m) => decode(m[1]).trim()), config })
    const bad = svgs.map((r, i) => r.error && `diagram ${i + 1}: ${r.error}`).filter(Boolean)
    if (bad.length) {
      console.error(`Mermaid could not render:\n  ${bad.join('\n  ')}`)
      process.exit(1)
    }
    let i = 0
    html = html.replace(/<pre data-mermaid>[\s\S]*?<\/pre>/g, () => `<div class="mermaid-svg">${svgs[i++].svg}</div>`)
  } finally {
    await browser.close()
  }
}

const names = [...new Set([...html.matchAll(/data-figure="([\w-]+)"/g)].map((m) => m[1]))]
if (names.length) {
  const ss = findStageshow()
  const esbuild = createRequire(join(ss, 'package.json'))('esbuild')
  const figures = names.map((name) => {
    const file = join(dirname(pagePath), 'figures', `${name}.tsx`)
    if (!existsSync(file)) {
      console.error(`data-figure="${name}" has no figures/${name}.tsx next to the page`)
      process.exit(1)
    }
    return { name, file }
  })
  const entry = [
    "import { createRoot } from 'react-dom/client'",
    ...figures.map((f, i) => `import F${i} from ${JSON.stringify(f.file)}`),
    'const mount = (name, C) => document.querySelectorAll(`[data-figure="${name}"]`).forEach((el) => createRoot(el).render(<C />))',
    ...figures.map((f, i) => `mount(${JSON.stringify(f.name)}, F${i})`),
  ].join('\n')

  const result = await esbuild.build({
    stdin: { contents: entry, loader: 'tsx', resolveDir: dirname(pagePath), sourcefile: 'figures-entry.tsx' },
    bundle: true,
    minify: true,
    format: 'iife',
    jsx: 'automatic',
    write: false,
    outdir: 'out',
    alias: { stageshow: ss, 'demo-page': SKILL },
    nodePaths: [join(ss, 'node_modules')],
    loader: { '.png': 'dataurl', '.jpg': 'dataurl', '.svg': 'dataurl', '.webp': 'dataurl' },
    define: { 'process.env.NODE_ENV': '"production"', 'import.meta.url': '"https://stageshow.invalid/kit/"' },
    logLevel: 'error',
  })
  const js = result.outputFiles.find((f) => f.path.endsWith('.js'))?.text ?? ''
  const css = result.outputFiles.find((f) => f.path.endsWith('.css'))?.text ?? ''
  html += `\n<style>\n${css}</style>\n<script>\n${js.replaceAll('</script', '<\\/script')}</script>\n`
}

mkdirSync(dirname(out), { recursive: true })
writeFileSync(`${out}.html`, html)
writeFileSync(
  `${out}.preview.html`,
  `<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n${html}\n</body></html>\n`,
)
console.log(`${out}.html\n${out}.preview.html`)

if (args.includes('--check')) {
  const { chromium } = createRequire(join(findStageshow(), 'package.json'))('playwright-core')
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' })
  try {
    // Reduced motion: every stageshow figure shows its poster, the still that tells its story
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' })
    const tab = await context.newPage()
    await tab.goto(pathToFileURL(`${out}.preview.html`).href, { waitUntil: 'networkidle' })
    await tab.evaluate(() => document.fonts.ready)
    await tab.waitForTimeout(500)
    await tab.screenshot({ path: `${out}.first-screen.png` })
    const text = await tab.evaluate(() => {
      for (const d of document.querySelectorAll('details')) d.open = true
      // A diagram is read by its title, not by its node labels
      for (const svg of document.querySelectorAll('svg.diagram, .mermaid-svg svg')) {
        const title = svg.querySelector('title')?.textContent?.trim()
        const note = document.createElement('p')
        note.textContent = title ? `[Diagram: ${title}]` : '[Diagram]'
        svg.replaceWith(note)
      }
      for (const stage of document.querySelectorAll('[data-figure]')) {
        const note = document.createElement('p')
        note.textContent = '[Animated figure: see the first-screen image for its still]'
        stage.replaceWith(note)
      }
      return document.body.innerText
    })
    writeFileSync(`${out}.txt`, text.replace(/\n{3,}/g, '\n\n'))
    console.log(`${out}.txt\n${out}.first-screen.png`)
  } finally {
    await browser.close()
  }
}

function findStageshow() {
  const candidates = [
    process.env.STAGESHOW_DIR,
    join(homedir(), '.claude/skills/stageshow'),
    join(homedir(), '.agents/skills/stageshow'),
    join(homedir(), '.codex/skills/stageshow'),
  ].filter(Boolean)
  const dir = candidates.find((d) => existsSync(join(d, 'kit/index.ts')))
  if (!dir) {
    console.error(`stageshow not found; set STAGESHOW_DIR. Looked in:\n  ${candidates.join('\n  ')}`)
    process.exit(1)
  }
  if (!existsSync(join(dir, 'node_modules/esbuild'))) {
    console.error(`stageshow has no node_modules; run: (cd ${dir} && npm install)`)
    process.exit(1)
  }
  return dir
}
