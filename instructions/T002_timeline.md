# T002_timeline — 時系列整理

## 目的

`incident_context.md` の事実を時系列に整理し、`timeline.md` を作成する。

## 入力

- `./incident_context.md`（必須）

## 作業

1. `incident_context.md` を読む。
2. `## 既知の事実` から時系列イベントを抽出する。
3. `../instructions/format.timeline.md` を読み、出力形式を把握する。
4. 手順2の内容を根拠に、`format.timeline.md` に従い `timeline.md` を作成する。
5. 変更してよいのは `timeline.md` のみ。

## 停止条件

- `incident_context.md` が存在しない、または `## 既知の事実` が空 → `abort.txt` に理由を書いて終了。
