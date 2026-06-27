**Languages:** [English](README.md) | [日本語](README.ja.md)

# agent_flow

ワークフローを事前設計し、実行を再現可能にする**実験的サンプル**。

設計も実行も AI に任せると、手順も品質も毎回ぶれる。**設計**はエージェント・オーケストレーションで対話的に試し、固まった順序・レビュー・ファイル制約を `main.py` と `instructions/` に書き固定する。**実行**は agent_flow が機械的に検証しながら段階実行し、同じ経路を繰り返す。

エージェント実装の例は [codex exec](https://developers.openai.com/codex/noninteractive)（[Codex](https://github.com/openai/codex) の非対話モード。`run_codex.py` が起動）。別エージェントへは `run_agent.py` の `ask_agent()` を差し替える。

## オーケストレーションとの棲み分け

エージェント・オーケストレーションは、常駐アシスタント・チャネル連携・スキル/ツール・マルチエージェント協調が中心。実行時にサブエージェントを起こし、動的に連携する向き。

agent_flow はその逆——設計済みフローを同じ形で回す実行エンジン。協調レイヤーやツール基盤は持たない。新規タスクの探索はオーケストレーション、定型フローの再現性は agent_flow。

## 実行

```bash
python main.py
```

- 成果物: `agent_out/`（自動作成）。正常終了時は `incident_context.md`, `timeline.md`, `hypothesis.md`（`action_required` のときは `action_plan.md` も）
- ログ: `logs/agent_stdout.log`（起動時にリセット、タスク間は追記。`logs/` も自動作成）
- 前提: Python 3.10+、`codex exec` が使えること（`codex` コマンドが PATH にあること）

## サンプルフロー（インシデント対応）

入力は `input/inbox/` に置く。形式不問。リポジトリ同梱のサンプル（`incident-memo.md` 等）が入っているので、そのまま試せる。自分の報告を使うときも、同じディレクトリにファイルを置けばよい。空なら何もしない。

```
inbox あり → T001_ingest → T002_timeline → T003_hypothesis
              → action_required なら T004_action_plan / monitor_only ならスキップ
```

各タスクは「作業 → レビュー（`*R.md`）→ NG なら差し戻し」。許可外のファイル変更はスナップショットから復元。

## 触る場所

フレームワークの上に載せる独自のワークフロー（タスク順序・分岐・指示・入力の扱い）を組み立てるとき、編集するのは左列だけ。右列はオーケストレーションの汎用部品なので触らない。


| 編集する                                              | 編集しない（フレームワーク）                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------- |
| `main.py` — パイプライン・パラメータ                          | `agent_task.py`, `run_agent.py`, `path_validators.py`, `app_config.py` |
| `instructions/` — `T00x.md`（作業）と `T00xR.md`（レビュー） | `fixed_instructions/`                                                  |
| `system_task.py` — 入力の存在確認など                      | `run_codex.py`（`codex exec` 起動。フラグの意味はファイル内コメント）                       |


パラメータは `main.py` 先頭の定数（`WORK_DIR`, `AGENT_TIMEOUT_SEC` 等）。

## フレームワークの要点

- **editable_files**: タスクごとに `work_dir` 内で変更可能なファイルを指定。外れた変更は差し戻し
  - **editable_files=None**: 成果物がないタスクはレビュー省略（検証対象がないため）
- **return_status**: 指定した戻り値を `main.py` で受け取り、後続タスクの実行を分岐可能
- **abort.txt**: 遂行不能時にエージェントが作成して中断
- **書き込み境界**: `work_dir` 外（inbox 等）への書き込みはエージェントのサンドボックスで防ぐ（`codex exec --sandbox workspace-write -C work_dir`）。フレームワークの差分検証は `work_dir` 内のみ
  - **検証除外**: ドットファイル（`.hidden` 等）、`work_dir` 外
- **単一プロセス**: 同一 `work_dir` の並行実行不可（スナップショット競合）

## エージェント差し替え

`AgentRunner` を実装し、`run_agent.ask_agent()` の委譲先を変更。`main.py` / `instructions/` はそのまま。

```python
def ask_agent(...) -> AgentResult:
    from run_claude import ClaudeRunner
    return ClaudeRunner().run(...)
```

作業ディレクトリ外への書き込みを制限する設定を含めること。