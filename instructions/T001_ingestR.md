# T001_ingest レビュー

## 入力

- `./incident_context.md`
- `../input/inbox/` 内のファイル

## レビュー基準

1. **事実のみ**: `## 既知の事実` に推測・仮説・原因が混入していないこと。
2. **入力反映**: 今回の入力ファイルの内容が `incident_context.md` に反映されていること。
3. **未確認の分離**: 判断できないことは `## 未確認事項` に書かれ、事実欄に混ざっていないこと。
4. **形式**: `../instructions/format.incident_context.md` に従っていること。

## 出力

`review.json` に `{"result":"OK"|"NG","reason":"..."}` を書く。
