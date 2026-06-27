# T001_ingest — インシデント情報取り込み

## 目的

`../input/inbox/` にある報告書・メモ・ログを読み、`incident_context.md` を**作成**する。  
このファイルは以降タスクの単一の事実ソースとなる。

## 入力

- `../input/inbox/` 内のファイル（JSON、Markdown、テキスト等。形式は問わない。1件以上必須）

## 作業

1. `../input/inbox/` 内のファイルをすべて読む（読み取りのみ。inbox 内のファイルは変更・削除しない）。
2. 既存の `incident_context.md` は参照しない。
3. `../instructions/format.incident_context.md` を読み、出力形式を把握する。
4. 手順1の内容を根拠に、`format.incident_context.md` に従い `incident_context.md` を新規作成（または上書き）する。
5. 変更してよいのは `incident_context.md` のみ。

## 停止条件

- `../input/inbox/` にファイルが1件もない → `abort.txt` に理由を書いて終了。
- ファイルが読めない、または内容から事実を抽出できない → `abort.txt` に理由を書いて終了。
