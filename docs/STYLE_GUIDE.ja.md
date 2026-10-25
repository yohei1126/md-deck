# スタイル Markdown とスライド記法

md-deck はレンダリングだけを担当し、見た目のテーマは同梱しません。デッキ用リポジトリが「本文 Markdown」と「スタイル Markdown」の 2 つを持ちます。スタイルファイルは、人間向けのスタイルガイドと、生成器用の設定を兼ねます。

**入力契約**（必須フロントマター、スキーマ、アセット、`md-deck check` の規則）は [INPUT_FORMAT.md](INPUT_FORMAT.md) を正とします。スタイル用の安定クラス／属性は [HOOKS.md](HOOKS.md) です。本ページはトークンと記法の一覧です。

## スタイルファイルの形

スタイルファイルは次の構成の Markdown です。

1. YAML フロントマター: テーマトークン
2. 本文の解説: 著者向け（生成器は無視）
3. 任意の `css` フェンス: トークン由来 CSS の後に追記

`--style path/to/deck_style.md` で渡すか、スライド側フロントマターに `style:` を書きます。CLI が優先です。解決できない場合はチェックが失敗します。

`examples/deck_style.md` はトークン一覧を示す白黒の見本です。製品デザインではありません。

## 必須トークンと任意トークン

必須（欠けるとチェック失敗）:

- `color_background`, `color_text`, `color_title`
- `font_family`, `font_size_body`

それ以外のトークンは任意で、省略時は英語版表のプレーン既定値を使います。未知の名前はエラーです。スキーマ: [`schemas/style.schema.json`](../schemas/style.schema.json)。

半径・枠線・余白の一部は `0` と `none` を許可します。ページ余白は `page_padding_top` など四辺トークンを個別に指定でき、省略した辺は `page_padding` を継承します。

## トークン一覧

長さの数値は `px` になります。例外は単位なしの `line_height` / `font_weight_title` / `font_weight_body` / `source_label_weight` です。色は CSS の色文字列である必要があります。

詳細な表は英語版 [STYLE_GUIDE.md](STYLE_GUIDE.md) を正とします。主なグループ:

- 必須色・フォント: `color_background`, `color_text`, `color_title`, `font_family`, `font_size_body`
- 追加色: `color_top_bar`, `color_accent_2`, `color_highlight`, `color_highlight_bg`, `color_gray`, `color_muted`
- ページ: `page_width`, `page_height`, `page_padding`, `page_padding_*`, `footer_inset_bottom`, `footer_inset_right`（負の値可）, `gap`
- その他の色: Key Message / Question / card / flow / table 向け
- タイポ: 各 `font_size_*`（表専用の `font_size_table` を含む）, `font_weight_*`, `line_height`
- 形: `card_radius`, `key_message_radius`, `question_radius`, `border_width`, `card_padding`（`0` / `none` 可）
- フロー: `flow_node_min_width`（既定 `120px`）, `flow_node_max_width`（既定 `none`。幅の上限なしで行を分け合う。`240px` のように長さを書くと中央に余白が残る）, `flow_node_min_height`（既定 `96px`。箱の床）, `flow_preferred_height`（既定 `60%`。`::: flow wide` でスタックがない一段がスライド内容領域のこの割合まで伸びる。`none` で中身の高さ。`220px` のように長さを書くとその高さまで）, `flow_fill_height`（既定 `none`。`fill` で余った高さまで伸ばし、`flow_preferred_height` の上限を外す）, `flow_stack_gap`（既定 `32px`。分岐スタックの箱のあいだ）, `flow_node_padding`, `flow_callout_gap`, `flow_port_gap`, `flow_edge_shape`（`orthogonal` / `straight`）
- カラム: `column_min_height`（既定 `160px`。`0` / `none` で中身の高さ）
- ラベル: `label_question`, `label_key_message`, `label_source`（省略時は `lang` から既定。`ja` なら「議論の問い」「キーメッセージ」「出典：」。`label_source: ""` で接頭辞を隠す）, `source_label_weight`（既定 `600`）, `source_label_gap`（既定 `0.15em`）
- 配置: `question_label_placement`（`inline` / `block`）、`page_number_placement`（`bottom-right` / `bottom-left` / `bottom-center`。出典フッターとは別）

## 任意の CSS フェンス

```css
.flow-node[data-kind="doc"] {
  background: var(--color-highlight-bg);
}
```

スタイルファイル内のすべての `css` フェンスが、生成された `:root` の後に連結されます。CLI の `--css file.css` はさらにその後です。`#slide-N` や `:nth-child()` ではなく [HOOKS.md](HOOKS.md) のフックを使ってください。

## スライド Markdown の約束

| 要素 | 書き方 | チェック |
| --- | --- | --- |
| スライド区切り | 行全体が `---` | 末尾の空スライド禁止 |
| タイトル | 各スライドちょうど 1 つの `# 見出し`。任意で `{#id .class}` | 不足・複数はエラー |
| Key Message | 各スライド最大 1 行の `**Key Message:** ...` | 複数はエラー |
| 問いボックス | `::: question` … `:::` | 空禁止 |
| 出典 | `Source:` / `出典:` 行、または `::: source` | 空の source ブロックはエラー |
| フロー | `::: flow` / `wide` / `straight` / `steps` / `fill`。矢印・lane・link・callout・stack・chips・`{#id}`・`shape=` | ノード 2 つ以上。未知オプション／種類／route／shape はエラー |
| カラム | `::: columns` / `plain` / `panel` / `fill` を `+++` で分割。中に `::: flow` を 1 段だけネスト可 | 非空カラム 2 つ以上。それ以外のネストは不可 |
| 改行 | 行末 `\`。フローのラベル／バッジ／タイトル、および H1 は `\n` 可。question/source 内は単一改行も改行扱い | |
| 表・リスト | 通常の Markdown。表の左上セルが空なら行見出し（`th[scope=row]`） | 列数一致、インデント。リスト項目の class は単純項目では `<p>` 化しない |
| コードフェンス | 閉じること | 未閉じはエラー |
| raw HTML | 原則不可 | `--allow-html` でのみ許可 |

フロー記法の詳細（ラベル付き矢印、破線、レーン、`link:` など）は [INPUT_FORMAT.md](INPUT_FORMAT.md) を参照してください。

スライド側フロントマターの必須キーは `title`, `version`, `date`, `lang`, `style` です。

## 見た目の方針

表現の上限、段階的な進め方、表紙タイトルの数値は [VISUAL_POLICY.md](VISUAL_POLICY.md)（英語）にあります。図のビフォーアフターは [DIAGRAMS.md](DIAGRAMS.md) と [`examples/diagram_patterns.md`](../examples/diagram_patterns.md) です。

スライド資料は、色を抑え、情報を構造化し、箱・矢印・分岐の骨子が読み取れる状態を目指します。装飾で目立たせることはしません。

- 1枚につき言いたいことは1つ。箱の中は文ではなく名前にする
- 比較は矢印ではなく `::: columns`（枠が要るときは `panel`、枠を消すときは `plain`）
- 分岐は1つの箱に「AまたはB」と書かず、結果ごとに箱と矢印を分ける
- 手順は `::: flow wide` の短い箱を横一列にする。行は中央に揃い、等間隔で、箱は行の幅を分け合う。`wide` の一段は `flow_preferred_height`（`60%`）まで伸び、枠もその高さに収まる。普通のフローは中身の高さのまま。タイトルは上端に置く。直後のキーメッセージもタイトル側に残し、その下のブロックを余白の中央に置く。末尾の `::: question` は下端に残し、余白は見出しの下と問いの上で分ける。余った高さまで伸ばすときは `flow_fill_height: fill` または `::: flow fill`。`steps` で小さな番号。分岐の起点の箱はラベルの幅、経路の箱は残りの列を分け合う。スタックの箱のあいだは `flow_stack_gap`（`32px`）。伸びたカラムの箇条書きはカードの高さに散らす
- スタイル側で `.flow-row { justify-content: space-between }` を指定してはいけない。中央揃えが消え、両端に寄る。新しい既定を使うときはその指定を外す
- 表紙（`data-cover="true"`）は中央揃え。フロントマターの `subtitle` と `date` がタイトルの下に出る。枠や大きなタイトルはデッキ側 CSS の任意指定で、生成器の既定にはしない

## 表紙タイトルの改行

表紙は先頭のスライドです。どのスライドでも `{.cover}` を付けるとそのスライドも表紙として検査します。先頭を表紙にしたくないときは `{.no-cover}` を付けます。

- 文の途中で折らない。折り返す位置は見出しの中の `\n` で指定する（`# 前の句\n後の句`）。行末の `\` では見出しは続きません
- 2行以上にするときは、行の長さを揃える。短い行は長い行の半分程度以上
- 和文で1行に収まらない表紙は `\n` が必要。欧文でも2行を超える長さなら `\n` が必要。`md-deck check` が、空行、4行以上、句の途中、長さの偏り、折り返し不足をエラーにする。先頭スライドが本文なら、そのエラーは `{.no-cover}` を案内する
- 2行目以降が「の」「を」などの助詞で始まるときは警告だけ出す。ビルドは止まらない
- 欧文で1回だけ自動折り返す場合は、タイトルの CSS `text-wrap: balance` が行の長さを揃える。最終確認は `md-deck build slides.md -o out.pdf --png out/png` で表紙（`data-cover="true"`）を見ること

```markdown
# 骨子を先に見せる\n色は抑えて残す {.cover}
```

## オーバーフロー

描画後、はみ出したスライドは 2% 刻みで最大 80% まで縮小します。それでも収まらなければ、スライド番号を出して失敗します。文章を短くするか、スタイル側のフォントサイズや余白を調整してください。
