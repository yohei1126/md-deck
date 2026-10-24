---
title: md-deck サンプル
version: "0.1.0"
date: "2026-10-24"
lang: ja
style: deck_style.md
subtitle: 入力契約と記法の見本
author: md-deck
audience: ツール利用者
---

# md-deck へようこそ

**Key Message:** Markdown 1 ファイルから、同じ入力なら同じ 16:9 PDF を生成する。

md-deck はレイアウトとビルドだけを担当します。見た目はデッキ側のスタイル Markdown が決めます。

---

# 箇条書きと表

**Key Message:** 通常の Markdown 記法（リスト・表）がそのままで使える。

- 入力はスライド用 Markdown
- 区切りは `---`
- 出力は PDF（必要なら PNG も）

| 項目 | 役割 |
| --- | --- |
| コンテンツ `.md` | スライド本文 |
| スタイル `.md` | 色・フォント・余白などのトークン |
| md-deck | HTML 化と PDF レンダリング |

---

# フロー図

**Key Message:** `::: flow` と `->` で手順を箱と矢印にする。

::: flow
Markdown -> HTML -> PDF
:::

---

# 2 カラム

**Key Message:** `::: columns` を `+++` で分割する。

::: columns
### 左：コンテンツ

- タイトル（`#`）
- Key Message
- 箇条書き・表

+++

### 右：スタイル

- YAML トークン
- 任意の `css` フェンス
- 人間向けの解説文
:::

---

# 問いを残す

**Key Message:** 議論用の枠は `::: question` で置く。

サンプルは中立なツール紹介です。業務名や社名は含めていません。

::: question
このサンプルを手元でビルドし、スタイル トークンを 1 つ変えて差分を確認してみてください。
:::
