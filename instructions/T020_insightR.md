## 手順

1. `../products/main_strategy.md` を読む。
2. `../instructions/format.t_insight.md` を読む。
3. `../instructions/format.t_data.md` を読み、`fetch_posts.py` を実行する。
   - `python3 ../t_data/fetch_posts.py --file market --limit 100 --unprocessed-only`
4. `./t_insight.md` を読む。
5. 手順2・4を照合し、見出し構成と観測分析の要件を満たしているか確認する。
6. 手順3の取得結果と手順4の記述が矛盾していないか確認する。
7. メイン戦略の転記・要約がないか確認する。
8. 戦略外テーマの観測が載っていないか確認する。
9. 判定結果を `review.json` に保存する。形式: `{"result":"OK","reason":"..."}` または `{"result":"NG","reason":"..."}`
