# スタイル Markdown とスライド記法

md-deck はレンダリングだけを担当し、見た目のテーマは同梱しません。デッキ用リポジトリが「本文 Markdown」と「スタイル Markdown」の 2 つを持ちます。スタイルファイルは、人間向けのスタイルガイドと、生成器用の設定を兼ねます。

## スタイルファイルの形

スタイルファイルは次の構成の Markdown です。

1. YAML フロントマター: テーマトークン
2. 本文の解説: 著者向け（生成器は無視）
3. 任意の `css` フェンス: トークン由来 CSS の後に追記

`--style path/to/deck_style.md` で渡すか、スライド側フロントマターに `style: deck_style.md` を書きます。どちらも無い場合は、理由を明示して失敗します。

`examples/deck_style.md` はトークン一覧を示す白黒の見本です。製品デザインではありません。デッキ用リポジトリにコピーして値を書き換えてください。

## トークン一覧

長さの数値は `px` になります。例外は単位なしの `line_height` / `font_weight_title` / `font_weight_body` です。文字列はそのまま出るので、`"1.5rem"` やフォントスタックを書けます。

詳細な表は英語版 [STYLE_GUIDE.md](STYLE_GUIDE.md) の Token schema を正とします。主なグループは次のとおりです。

- ページ: `page_width`, `page_height`, `page_padding`, `gap`
- 色: `color_background`, `color_text`, `color_title`, Key Message / Question / card / flow / table 向けの各色
- タイポ: `font_family`, 各 `font_size_*`, `font_weight_*`, `line_height`
- 形: `card_radius`, `key_message_radius`, `question_radius`, `border_width`, `card_padding`
- フロー: `flow_node_min_width`, `flow_node_padding`

未知のトークン名はエラーです。省略したトークンはドキュメント記載のプレーンな既定値で埋めます（ブランドテーマではありません）。

## 任意の CSS フェンス

```css
.slide h1 {
  letter-spacing: 0.02em;
}
```

スタイルファイル内のすべての `css` フェンスが、生成された `:root` の後に連結されます。CLI の `--css file.css` はさらにその後です。

## スライド Markdown の約束

| 要素 | 書き方 |
| --- | --- |
| スライド区切り | 行全体が `---` |
| タイトル | `# 見出し` |
| Key Message | 行頭の `**Key Message:** ...` |
| 問いボックス | `::: question` … `:::` |
| フロー | `::: flow` 内で `A -> B -> C`（または 1 行 1 ノード）… `:::` |
| カラム | `::: columns` を `+++` 行で分割 … `:::` |
| 表・リスト | 通常の Markdown |

スライド側フロントマターには `title:`（PDF タイトル）と `style:`（スタイル Markdown への相対パス）を置けます。

## オーバーフロー

描画後、はみ出したスライドは 2% 刻みで最大 80% まで縮小します。それでも収まらなければ、スライド番号を出して失敗します。文章を短くするか、スタイル側のフォントサイズや余白を調整してください。
