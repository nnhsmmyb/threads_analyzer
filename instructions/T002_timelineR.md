# T002_timeline レビュー

## 入力

- `./incident_context.md`
- `./timeline.md`

## レビュー基準

1. **事実と推測の分離**: タイムラインに推測・仮説・原因が含まれていないこと。
2. **根拠**: 各行の `根拠` が `incident_context.md` の記述に対応していること。
3. **網羅**: `incident_context.md` の主要な事実がタイムラインに漏れなく反映されていること。
4. **時系列**: 時刻が昇順（または降順）で一貫していること。
5. **形式**: `../instructions/format.timeline.md` に従っていること。

## 出力

`review.json` に `{"result":"OK"|"NG","reason":"..."}` を書く。
