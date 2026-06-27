# T004_action_plan レビュー

## 入力

- `./incident_context.md`
- `./hypothesis.md`
- `./action_plan.md`

## レビュー基準

1. **仮説との対応**: 各アクションが `hypothesis.md` の仮説 ID に対応していること。
2. **ロールバック**: `## 即時対応` の各行にロールバック手順があること。
3. **影響範囲**: `incident_context.md` の `## 影響範囲` を考慮した対応であること。
4. **エスカレーション**: `## エスカレーション条件` が具体的であること。
5. **形式**: `../instructions/format.action_plan.md` に従っていること。

## 出力

`review.json` に `{"result":"OK"|"NG","reason":"..."}` を書く。
