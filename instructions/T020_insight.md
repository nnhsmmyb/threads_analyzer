## 手順

1. `../products/main_strategy.md` を読み、最上位戦略を把握する。
2. `../instructions/format.t_data.md` を読み、`fetch_posts.py` の実行方法を把握する。
3. 手順2に従い `fetch_posts.py` を実行する。
   - `python3 ../t_data/fetch_posts.py --file market --limit 100 --unprocessed-only`
4. `./t_insight.md` があれば読み、既存の観測知識を把握する。
5. `../instructions/format.t_insight.md` を読み、出力形式を把握する。
6. 手順3の取得結果を根拠に、`format.t_insight.md` に従い `t_insight.md` を更新する。メイン戦略に合致するデータだけを書く。
