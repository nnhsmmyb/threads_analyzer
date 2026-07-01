# autoT

Threads 市場観測の最小パイプライン（[agent_flow](https://github.com/nnhsmmyb/agent_flow) ベース）。

```
data_suggestion_weekly.json → Threads API fetch → ingest → T020_insight → t_insight.md
```

## セットアップ

```bash
cp .env.example .env
# THREADS_ACCESS_TOKEN を設定

cp samples/data_suggestion_weekly.json agent_out/
```

## 実行

```bash
python3 main.py           # fetch + ingest + insight
python3 main.py --no-fetch  # ingest + insight のみ（既存 JSON / ストック利用）
```

## ディレクトリ

| 場所 | 役割 |
| --- | --- |
| `agent_out/` | `data_suggestion_weekly.json`, `t_insight.md` |
| `input/threads/` | fetch 結果 JSON（INGEST 後に空になる） |
| `t_data/` | 分類済みストック（`t_data_market.yaml`） |
| `instructions/` | T020 タスク手順 |
| `products/` | `main_strategy.md` |

## App Review

録画対象: OAuth → `python3 main.py` → `agent_out/t_insight.md` まで。

## フレームワーク

`agent_task.py`, `run_agent.py`, `run_codex.py` は agent_flow のまま。ワークフローは `main.py` と `instructions/` を編集する。
