import type { LookTokens, Theme } from 'stageshow/kit'

// The Journal look for stageshow figures: spread it on the Stage.
//   <Stage {...JOURNAL} width={720} height={340} ...>
// The well matches the page's panel, so the stage reads as one of the page's
// panels; the accent is the page's clay.
export const JOURNAL: { theme: Theme; tokens: LookTokens } = {
  theme: 'light',
  tokens: {
    '--ss-well': '#f0eee6',
    '--ss-accent': '#b0532c',
    '--ss-accent-soft': 'rgba(176, 83, 44, 0.16)',
    '--ss-accent-text': '#a04a26',
  },
}
