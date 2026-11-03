import { Avatar, Bar, Collapse, Count, Field, Icon, Row, Stage, Window, type Act } from 'stageshow/kit'
import { JOURNAL } from 'demo-page/figure/look'
import './search.css'

// Admin console search, answered in the browser. The agent types "acme";
// the list narrows on every keystroke, each query timed locally, and the
// Network panel never gains a request.

type S = { focused: boolean; q: string; picked: boolean }

const initial: S = { focused: false, q: '', picked: false }
const POSTER: S = { focused: true, q: 'acme', picked: true }

const ACCOUNTS = [
  'Acme Corp',
  'Brightline Freight',
  'Atlas Dental',
  'Acme Logistics',
  'Acorn Studio',
  'Corvid Labs',
  'Acme Health',
  'Acme Robotics',
]
// Subtitle and meta widths, varied row to row
const W = [[92, 34], [70, 30], [84, 36], [64, 32], [96, 28], [74, 34], [88, 30], [68, 36]]
// What the local index took for each query, in ms
const MS: Record<string, number> = { a: 41, ac: 36, acm: 39, acme: 38 }

const matches = (name: string, q: string) => !q || name.toLowerCase().split(' ').some((w) => w.startsWith(q))

function Title({ name, q }: { name: string; q: string }) {
  // Every letter keeps its own span, so a match only recolors in place
  const hit = !!q && name.toLowerCase().startsWith(q)
  return (
    <>
      {[...name].map((c, i) => (
        <span key={i} className="sd-ch" data-hit={(hit && i < q.length) || undefined}>
          {c}
        </span>
      ))}
    </>
  )
}

async function script(a: Act<S>) {
  await a.wait(700)
  await a.move('search')
  await a.wait(150)
  await a.click()
  await a.set({ focused: true })
  await a.wait(350)
  // One key at a time, slow enough to see each query narrow the list
  const query = 'acme'
  for (let i = 1; i <= query.length; i++) {
    await a.set({ q: query.slice(0, i) })
    await a.wait(i === query.length ? 300 : 520)
  }
  await a.set({ picked: true })
  await a.move('rest')
  await a.wait(2600)
  // Clearing the field is the visible cause of the reset
  await a.move('clear')
  await a.wait(200)
  await a.click()
  await a.set({ q: '', picked: false })
  await a.wait(500)
  await a.set({ focused: false })
  await a.move('rest')
  await a.wait(400)
}

export default function SearchDemo() {
  return (
    <Stage
      width={720}
      height={340}
      compact={{ below: 600, width: 358, height: 320 }}
      initial={initial}
      poster={POSTER}
      script={script}
      {...JOURNAL}
      cursor={{ at: { wide: { x: 600, y: 300 }, compact: { x: 300, y: 280 } } }}
      className="sd"
    >
      {(s, _rect, layout) => {
        const shown = ACCOUNTS.map((n) => matches(n, s.q))
        const first = shown.indexOf(true)
        return (
          <>
            <Window
              className="sd-window"
              title="Accounts"
              sidebar={layout === 'wide' ? <Side /> : undefined}
              sidebarWidth={148}
            >
              <div className="sd-body">
                <Field
                  className="sd-field"
                  value={s.q}
                  placeholder="Search accounts"
                  focused={s.focused}
                  leading={<Icon name="search" size={14} />}
                  trailing={
                    <span className="sd-trail">
                      <span className="sd-ms" data-show={!!s.q || undefined}>
                        <Count value={MS[s.q] ?? 38} format={(n) => `${n} ms`} duration={320} />
                      </span>
                      <span className="sd-clear" data-show={!!s.q || undefined} data-target="clear" data-cursor="pointer">
                        <Icon name="close" size={12} stroke={2} />
                      </span>
                    </span>
                  }
                  box={{ 'data-target': 'search', 'data-cursor': 'ibeam' }}
                />
                <div className="sd-list" data-crop>
                  {ACCOUNTS.map((name, i) => (
                    <Collapse key={name} open={shown[i]}>
                      <Row
                        pad={10}
                        selected={s.picked && i === first}
                        lead={<Avatar name={name} size={28} />}
                        title={<Title name={name} q={s.q} />}
                        subtitle={<Bar w={W[i][0]} h={6} tone={2} />}
                        meta={<Bar w={W[i][1]} h={6} tone={2} />}
                      />
                    </Collapse>
                  ))}
                </div>
              </div>
            </Window>

            {layout === 'wide' && (
              <div className="sd-net" aria-hidden>
                <div className="sd-net-head">
                  <span>Network</span>
                  <span className="sd-net-filter">Fetch/XHR</span>
                </div>
                <div className="sd-net-row">
                  <span className="sd-net-name">index-snapshot.bin</span>
                  <span className="sd-net-size">1.8 MB</span>
                </div>
                <div className="sd-net-foot">
                  <span>Search requests</span>
                  <span className="sd-net-zero">0</span>
                </div>
              </div>
            )}
            <span data-target="rest" className="sd-rest" />
          </>
        )
      }}
    </Stage>
  )
}

function Side() {
  return (
    <div className="sd-side">
      {[58, 72, 50, 64, 44].map((w, i) => (
        <div key={i} className="sd-side-item" data-active={i === 1 || undefined}>
          <Bar w={12} h={12} r={3} tone={i === 1 ? 4 : 3} />
          <Bar w={w} h={6} tone={i === 1 ? 4 : 2} />
        </div>
      ))}
    </div>
  )
}
