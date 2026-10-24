# スタイル Markdown とスライド記法

md-deck はレンダリングだけを担当し、見た目のテーマは同梱しません。デッキ用リポジトリが「本文 Markdown」と「スタイル Markdown」の 2 つを持ちます。スタイルファイルは、人間向けのスタイルガイドと、生成器用の設定を兼ねます。

**入力契約**（必須フロントマター、スキーマ、アセット、`md-deck check` の規則）は [INPUT_FORMAT.md](INPUT_FORMAT.md) を正とします。本ページはトークンと記法の一覧です。

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

## トークン一覧

長さの数値は `px` になります。例外は単位なしの `line_height` / `font_weight_title` / `font_weight_body` です。色は CSS の色文字列である必要があります。

詳細な表は英語版 [STYLE_GUIDE.md](STYLE_GUIDE.md) を正とします。主なグループ:

- 必須色・フォント: `color_background`, `color_text`, `color_title`, `font_family`, `font_size_body`
- ページ: `page_width`, `page_height`, `page_padding`, `gap`
- その他の色: Key Message / Question / card / flow / table 向け
- タイポ: 各 `font_size_*`, `font_weight_*`, `line_height`
- 形: `card_radius`, `key_message_radius`, `question_radius`, `border_width`, `card_padding`
- フロー: `flow_node_min_width`, `flow_node_padding`

## 任意の CSS フェンス

```css
.slide h1 {
  letter-spacing: 0.02em;
}
```

スタイルファイル内のすべての `css` フェンスが、生成された `:root` の後に連結されます。CLI の `--css file.css` はさらにその後です。

## スライド Markdown の約束

| 要素 | 書き方 | チェック |
| --- | --- | --- |
| スライド区切り | 行全体が `---` | 末尾の空スライド禁止 |
| タイトル | 各スライドちょうど 1 つの `# 見出し` | 不足・複数はエラー |
| Key Message | 各スライド最大 1 行の `**Key Message:** ...` | 複数はエラー |
| 問いボックス | `::: question` … `:::` | 空禁止。種類は question/flow/columns のみ |
| フロー | `::: flow` 内で `A -> B` … `:::` | ノード 2 つ以上。空ノード禁止 |
| カラム | `::: columns` を `+++` 行で分割 … `:::` | 非空カラム 2 つ以上。`+++` は columns 内のみ |
| 表・リスト | 通常の Markdown | 列数一致、インデント |
| コードフェンス | 閉じること | 未閉じはエラー |
| raw HTML | 原則不可 | `--allow-html` でのみ許可 |

スライド側フロントマターの必須キーは `title`, `version`, `date`, `lang`, `style` です（[INPUT_FORMAT.md](INPUT_FORMAT.md)）。

## オーバーフロー

描画後、はみ出したスライドは 2% 刻みで最大 80% まで縮小します。それでも収まらなければ、スライド番号を出して失敗します。文章を短くするか、スタイル側のフォントサイズや余白を調整してください。
