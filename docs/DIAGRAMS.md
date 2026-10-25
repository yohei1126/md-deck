# Diagram patterns

Three patterns cover most of the bone a slide needs: a 2-box compare, a branch, and a 3-step horizontal row. Each pair below is valid Markdown. The "before" slide builds; it fails the [visual policy](VISUAL_POLICY.md), not the checker. The checker does not score sentence length.

The buildable deck is [`examples/diagram_patterns.md`](../examples/diagram_patterns.md). HTML below is what the generator emits before `deck.js` measures the page. `.flow-edge` elements are data. At PDF time they become SVG `.flow-arrow` paths. Arrow coordinates are not part of the example.

Listings are whitespace-normalized. Pair-index attributes on edges are omitted. Long "before" paragraphs are shortened with an ellipsis; the example file has the full sentences.

## 2-box compare

Use two columns with the same kind of line on each side. An arrow means a sequence, so it is the wrong bone for a comparison.

### Before

```markdown
::: columns
## How it works today

The team copies text into a document, edits it in several places, and exports a PDF whenever someone asks. Readers cannot tell which export is current.

+++

## How it could work

One Markdown file is checked in CI and the PDF is rebuilt from the same bytes, so review comments point at a line instead of a screenshot.
:::
```

```html
<div class="columns">
  <div class="column">
    <h2 class="column-head">How it works today</h2>
    <p>The team copies text into a document, edits it in several places, …</p>
  </div>
  <div class="column">
    <h2 class="column-head">How it could work</h2>
    <p>One Markdown file is checked in CI and the PDF is rebuilt from the same bytes, …</p>
  </div>
</div>
```

### After

```markdown
::: columns panel
## Current

- Many owners
- Manual export
- Hard to diff

+++

## Proposed

- One generator
- Same PDF bytes
- Check in CI
:::
```

```html
<div class="columns panel">
  <div class="column">
    <h2 class="column-head">Current</h2>
    <ul>
      <li>Many owners</li>
      <li>Manual export</li>
      <li>Hard to diff</li>
    </ul>
  </div>
  <div class="column">
    <h2 class="column-head">Proposed</h2>
    <ul>
      <li>One generator</li>
      <li>Same PDF bytes</li>
      <li>Check in CI</li>
    </ul>
  </div>
</div>
```

What changed: the two sides became parallel bullets under short headings, three lines each, same grammar. `panel` marks the pair as cards (the border itself comes from `.column` unless the block is `plain`). There is no `.flow-edge`. The eye compares across the row instead of reading two paragraphs.

## Branch / fork

Each outcome is a box. Each outcome gets its own arrow. One label that says "choose A or B" hides the branch.

`Start -> { Keep / Change }` is **not** this pattern. That chain attaches a single arrow to the middle of the stack. Fan into each member with a separate edge.

A same-row fan (`Start -> Keep` and `Start -> Change` as three boxes in one row) is routed, but it is easy to misread as the sequence Start → Keep → Change. Prefer the stack.

### Before

```markdown
::: flow
Start -> Choose keep or change
:::
```

```html
<div class="flow">
  <div class="flow-lanes">
    <div class="lane" data-lane="0">
      <div class="flow-row">
        <div class="flow-node" data-node="Start">
          <span class="flow-node-title">Start</span>
        </div>
        <div class="flow-node" data-node="Choose keep or change">
          <span class="flow-node-title">Choose keep or change</span>
        </div>
      </div>
      <div class="flow-edge" data-from="Start" data-to="Choose keep or change"
           data-style="solid" data-kind="solid"></div>
    </div>
  </div>
</div>
```

### After

```markdown
::: flow
Start {#start}
{ Keep / Change }
{#start} -> Keep
{#start} -> Change
:::
```

```html
<div class="flow">
  <div class="flow-lanes">
    <div class="lane" data-lane="0">
      <div class="flow-row">
        <div class="flow-node" data-node="start" data-id="start">
          <span class="flow-node-title">Start</span>
        </div>
        <div class="flow-stack">
          <div class="flow-node" data-node="Keep">
            <span class="flow-node-title">Keep</span>
          </div>
          <div class="flow-node" data-node="Change">
            <span class="flow-node-title">Change</span>
          </div>
        </div>
      </div>
      <div class="flow-edge" data-from="start" data-to="Keep"
           data-style="solid" data-kind="solid"></div>
      <div class="flow-edge" data-from="start" data-to="Change"
           data-style="solid" data-kind="solid"></div>
    </div>
  </div>
</div>
```

What changed: the choice left the second label and became two nodes inside `.flow-stack`. Two edges leave `start`, one per outcome. The renderer draws them as one trunk that splits, with a horizontal run into the middle of each box long enough for the arrowhead. The row keeps at least 72px between Start and the stack, and the two outcome boxes keep `flow_stack_gap` (default `32px`) between them. The pair stays centred, so the heads do not sit in the corners. Labels are names.

## 3-step horizontal

A procedure of three beats is a row of boxes, not a numbered paragraph list.

### Before

```markdown
1. Someone gathers notes from several places and pastes them into a document that keeps growing.
2. A reviewer reads the whole document and tries to decide what changed since last time.
3. Another person exports a PDF by hand and emails it, so the next reader is never sure which file is current.
```

```html
<ol>
  <li>Someone gathers notes from several places and pastes them into a document that keeps growing.</li>
  <li>A reviewer reads the whole document and tries to decide what changed since last time.</li>
  <li>Another person exports a PDF by hand and emails it, so the next reader is never sure which file is current.</li>
</ol>
```

### After

```markdown
::: flow wide steps
Collect -> Decide -> Record
:::
```

```html
<div class="flow flow-steps flow-wide">
  <div class="flow-lanes">
    <div class="lane" data-lane="0">
      <div class="flow-row">
        <div class="flow-node" data-node="Collect">
          <span class="flow-node-title">Collect</span>
        </div>
        <div class="flow-node" data-node="Decide">
          <span class="flow-node-title">Decide</span>
        </div>
        <div class="flow-node" data-node="Record">
          <span class="flow-node-title">Record</span>
        </div>
      </div>
      <div class="flow-edge" data-from="Collect" data-to="Decide"
           data-style="solid" data-kind="solid"></div>
      <div class="flow-edge" data-from="Decide" data-to="Record"
           data-style="solid" data-kind="solid"></div>
    </div>
  </div>
</div>
```

What changed: the `ol` of sentences became three `.flow-node` boxes and two edges, Collect → Decide → Record. `wide` keeps them on one row, centred, with the same gap between boxes. Each box shares the row (`flow_node_max_width` defaults to `none`) and stays as tall as its label, with a `flow_node_min_height` floor (default `96px`). `steps` paints a muted index above each name via `.flow-node-title::before`. `::: flow wide steps fill`, or the style token `flow_fill_height: fill`, is what stretches those boxes to the height left under the title. A flow with a callout does not take that extra height.

A deck style must not set `justify-content: space-between` on `.flow-row` or `.flow.flow-wide .flow-row`. That declaration cancels the centring and pins Collect and Record to the edges. Remove it. The default already shares the row; a length on `flow_node_max_width` is what puts the side inset back.

## One sentence and three cards

A conclusion plus three parallel cards does not need a new block. The Key Message is the sentence. `::: columns` already accepts more than two parts.

```markdown
**Key Message:** One sentence can sit over three parallel cards.

::: columns panel
## Collect

One owner

+++

## Decide

One check

+++

## Record

One file
:::
```

```html
<div class="key-message">…</div>
<div class="columns panel">
  <div class="column"><h2 class="column-head">Collect</h2><p>One owner</p></div>
  <div class="column"><h2 class="column-head">Decide</h2><p>One check</p></div>
  <div class="column"><h2 class="column-head">Record</h2><p>One file</p></div>
</div>
```

What changed from a 2-box compare: a third column, and a single sentence above the cards. Each card stays one short line. Column cards have a `column_min_height` floor (default `160px`) and stretch with the row. `::: columns fill` asks them to take the height still free on the slide. Bullets inside a column keep a `1.4em` indent even when the deck style zeroes `ul` padding.

## Cover title on the same deck

The last slide of the example is a cover (class `cover`) whose break is explicit:

```markdown
# 骨子を先に見せる\n色は抑えて残す {.cover}
```

```html
<h1 class="cover title">骨子を先に見せる<br>色は抑えて残す</h1>
```

The section also has `data-cover="true"`. Rules and the PNG check are in [VISUAL_POLICY.md](VISUAL_POLICY.md).
