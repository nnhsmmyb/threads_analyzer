# T003_hypothesis レビュー

## 入力

- `./incident_context.md`
- `./timeline.md`
- `./hypothesis.md`

## レビュー基準

1. **根拠**: 各仮説の `根拠` が `timeline.md` の具体的イベントを参照していること。
2. **飛躍なし**: timeline にない事実を根拠にした仮説がないこと。
3. **信頼度**: 信頼度（高/中/低）が根拠の強さと整合していること。
4. **対応要否**: 信頼度「高」「中」の仮説がある場合、即時対応が必要な内容になっていること（`action_required` 相当の判断根拠があること）。
5. **形式**: `../instructions/format.hypothesis.md` に従っていること。

## 出力

`review.json` に `{"result":"OK"|"NG","reason":"..."}` を書く。
