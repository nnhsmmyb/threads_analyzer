# T003_hypothesis — 原因仮説

## 目的

タイムラインの事実に基づき、原因仮説を `hypothesis.md` にまとめる。

## 入力

- `./incident_context.md`（必須）
- `./timeline.md`（必須）

## 作業

1. `incident_context.md` と `timeline.md` を読む。
2. `../instructions/format.hypothesis.md` を読み、出力形式と `result.json` の判定基準を把握する。
3. 手順1の内容を根拠に、`format.hypothesis.md` に従い `hypothesis.md` を作成する。
4. 即時対応の要否を判定し、`result.json` に書く（判定基準は `format.hypothesis.md` を参照）。
5. 変更してよいのは `hypothesis.md` と `result.json` のみ。

## 停止条件

- `timeline.md` が存在しない、またはイベントが空 → `abort.txt` に理由を書いて終了。
