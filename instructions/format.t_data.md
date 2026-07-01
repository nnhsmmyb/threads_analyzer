## `fetch_posts.py`

`agent_out/` から実行する。`t_data/` は直接開かない。

```bash
python3 ../t_data/fetch_posts.py --file market --limit 100 --unprocessed-only
```

| オプション | 意味 |
|-----------|------|
| `--file` | `market` のみ |
| `--limit` | 返す件数（1〜100、新しい順） |
| `--unprocessed-only` | `processed: false` のみ |

### 投稿レコードの主なフィールド

| フィールド | 意味 |
|-----------|------|
| `post_id` | Threads media ID |
| `text` | 本文 |
| `username` | 投稿者 |
| `permalink` | 投稿 URL |
| `posted_at` | 投稿日時 |
| `captured_at` | fetch 日時 |
| `fetch_purpose` | 取得目的 |
| `processed` | 分析済みフラグ（false=未分析） |
