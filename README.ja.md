# threads_analyzer

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
python3 main.py
python3 main.py --no-fetch
```

## 触る場所

| 編集する | 編集しない |
| --- | --- |
| `main.py` | `agent_task.py`, `run_agent.py` |
| `instructions/` | `run_codex.py`, `app_config.py` |
| `threads_api_system.py`, `t_data_system.py` | `fixed_instructions/agent_prompt.md` |

## App Review

全 11 permission テスト（`review_test/`）:

```bash
python3 threads_oauth_setup.py --manual   # スコープ変更後は必須
python3 review_test/run.py
```

詳細: [review_test/README.md](review_test/README.md)

本番パイプライン: OAuth → `python3 main.py` → `t_insight.md`
