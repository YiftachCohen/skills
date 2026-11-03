import { Avatar, Bar, Caret, Check, Collapse, Icon, Prompt, Row, Spinner, Stage, States, Text, Window, type Act } from 'stageshow/kit'
import { JOURNAL } from 'demo-page/figure/look'
import './wait.css'

// A review lands while CI is still running, then a check times out. The wait
// script holds the first event for its settle window and returns both in one
// result, so the agent fixes them in one push. Then it runs again.

type Status = 'running' | 'passed' | 'timedout'
type S = { a: Status; b: Status; review: boolean; result: boolean }

const initial: S = { a: 'running', b: 'running', review: false, result: false }
const POSTER: S = { a: 'passed', b: 'timedout', review: true, result: true }

async function script(a: Act<S>) {
  await a.wait(900)
  await a.set({ a: 'passed' })
  await a.wait(1500)
  await a.set({ review: true })
  await a.wait(1600)
  await a.set({ b: 'timedout' })
  await a.wait(1100)
  await a.set({ result: true })
  await a.wait(3000)
  // Exit around the anchor: what the run added leaves in one reverse stagger,
  // the checks go back to running for the next run, and the loop starts over
  await a.set({ result: false })
  await a.wait(70)
  await a.set({ review: false })
  await a.wait(70)
  await a.set({ b: 'running' })
  await a.wait(70)
  await a.set({ a: 'running' })
  await a.wait(600)
}

function Mark({ status }: { status: Status }) {
  return (
    <States
      value={status}
      className="wt-mark"
      states={{
        running: <Spinner size={16} className="wt-spin" />,
        passed: <Check on size={16} className="wt-pass" />,
        timedout: (
          <span className="wt-fail">
            <Icon name="close" size={10} stroke={2.5} />
          </span>
        ),
      }}
    />
  )
}

function Meta({ status }: { status: Status }) {
  return (
    <States
      value={status}
      align="end"
      className="wt-meta"
      states={{ running: <span>Running</span>, passed: <span>Passed</span>, timedout: <span className="wt-bad">Timed out</span> }}
    />
  )
}

export default function WaitFigure() {
  return (
    <Stage {...JOURNAL} width={720} height={340} compact={{ below: 600, width: 358, height: 358 }} initial={initial} poster={POSTER} script={script} className="wt">
      {(s, _rect, layout) => (
        <>
          <Window className="wt-window" title="babysit-pr: fix the CI wait loop" sidebar={layout === 'wide' ? <Side /> : undefined} sidebarWidth={148}>
            <div className="wt-body">
              <div className="wt-label">Checks</div>
              <div className="wt-list">
                <Row pad={8} lead={<Mark status={s.a} />} title={<Text>test (3.8)</Text>} meta={<Meta status={s.a} />} />
                <Row pad={8} lead={<Mark status={s.b} />} title={<Text>test (3.12)</Text>} meta={<Meta status={s.b} />} />
              </div>
              <div className="wt-label">Activity</div>
              <div className="wt-list">
                <Collapse open={s.review} reveal="drop">
                  <Row pad={8} lead={<Avatar name="Dana" size={24} />} title={<Text>Dana requested changes</Text>} subtitle={<Text className="wt-quote">Quote "$SHA" in the gh call</Text>} />
                </Collapse>
                <Row pad={8} lead={<Avatar plain size={24} />} title={<Bar w={120} h={6} tone={2} />} subtitle={<Bar w={180} h={6} tone={1} />} />
                <Row pad={8} lead={<Avatar plain size={24} />} title={<Bar w={96} h={6} tone={2} />} subtitle={<Bar w={150} h={6} tone={1} />} />
              </div>
            </div>
          </Window>

          <Window chrome="terminal" lights="grey" className="wt-term" title={layout === 'wide' ? 'zsh' : undefined}>
            <div className="ss-term wt-term-body">
              <Prompt path="~">wait-for-pr.sh 15 --required</Prompt>
              <States
                value={s.result ? 'out' : 'wait'}
                align="start"
                className="wt-line"
                states={{
                  wait: <Caret />,
                  out: (
                    <span>
                      WAIT_RESULT: <span className="err">failing</span>,<span className="ok">new-review</span>
                    </span>
                  ),
                }}
              />
              {layout === 'wide' && (
                <div className="wt-out dim" data-show={s.result || undefined}>
                  {'{ "expected_sha": "049e282", …'}
                </div>
              )}
            </div>
          </Window>
        </>
      )}
    </Stage>
  )
}

function Side() {
  return (
    <div className="wt-side">
      {[58, 72, 50, 64].map((w, i) => (
        <div key={i} className="wt-side-item">
          <Bar w={12} h={12} r={3} tone={i === 1 ? 4 : 3} />
          <Bar w={w} h={6} tone={i === 1 ? 4 : 2} />
        </div>
      ))}
    </div>
  )
}
