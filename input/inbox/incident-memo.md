# 障害報告メモ

報告者: 田中（SRE）
報告日時: 2025-06-08 14:35 JST

## 概要

14:28 頃から payment-api の 5xx が急増。監視アラート発火。

## 確認できたこと

- api-server 3台すべてで DB 接続タイムアウト
- postgres-primary への接続が 30秒でタイムアウト
- api-gateway 経由の POST /v1/payments が 503 を返している

## まだわかっていないこと

- postgres-primary が応答しない直接の原因
- フェイルオーバーは実行されたか
