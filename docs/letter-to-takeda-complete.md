# 武田先生宛 完了ご報告メール（下書き）

> Gmail / Outlook 等にコピペしてご利用ください。

---

**件名：** 【完了】IRDB 日本語論文への OpenAlex Topic 再付与 全件処理完了のご報告

---

武田先生

お世話になっております。
iGroup Japan の笠間でございます。

先日（5 月 18 日）ご連絡いたしました IRDB 日本語論文への OpenAlex Topic 再付与につきまして、**全件処理が完了**いたしましたのでご報告申し上げます。

## 処理結果サマリ

| 項目 | 値 |
|---|---|
| 処理件数 | **2,499,476 件**（スキップ 0 件） |
| 処理時間 | 約 27.6 時間 |
| 出力形式 | JSONL（gzip 圧縮後 165 MB） |
| 付与方式 | すべて埋め込みベース（multilingual-e5-base） |

## 品質概要

| 指標 | 値 |
|---|---|
| primary_topic 平均スコア | **0.7962**（最低 0.68、最高 0.90） |
| score ≥ 0.7 の件率 | **100.0 %** |
| カバーした OpenAlex Topic 種類 | **4,515 / 4,516 種**（タクソノミーほぼ全網羅） |

全件で信頼度スコア 0.7 以上を確保しており、低信頼度のレコードは皆無でした。詳細は添付の品質評価レポートをご参照ください。

## 添付資料

1. **技術メモ**（`technical-memo-for-Prof_takeda.pdf`）  
   モデル選定根拠・パイプライン構成・1k サンプル評価結果

2. **品質評価レポート・全件版**（`quality-report-full.pdf`）  
   全 2,499,476 件のスコア分布・Topic カバレッジ・既知の限界

## 出力フォーマット（OpenAlex Work スキーマ準拠）

各 Work に対して以下の形式で出力しています：

```json
{
  "work_id": "https://openalex.org/W2781293634",
  "primary_topic": {
    "id": "https://openalex.org/T10318",
    "display_name": "Machine Learning in Healthcare",
    "score": 0.7790
  },
  "topics": [
    { "id": "...", "display_name": "Machine Learning in Healthcare",        "score": 0.7790 },
    { "id": "...", "display_name": "Biomedical Text Mining and Ontologies", "score": 0.7621 },
    { "id": "...", "display_name": "Clinical Decision Support Systems",     "score": 0.7488 }
  ],
  "method": "embedding"
}
```

## ソースコード・関連リンク

- **GitHub リポジトリ（MIT ライセンス）：**  
  https://github.com/KKasama/OpenAlex-Topics-assignment-for-IRDB

再現性の担保と、必要であれば NII 側でも追試いただけるよう設計しております。

## ご相談事項

本結果データを OpenAlex（CTO の Jason Priem 氏）に提供・共有することについて、NII・IRDB の観点からご懸念がないかご確認いただけますでしょうか。

1. 本データの OpenAlex への提供・共有について問題がないかどうか
2. 公表・共有に際して確認すべき制約事項
3. （差し支えなければ）NII・IRDB 側でも本データの活用にご関心がおありか

お忙しいところ大変恐縮ですが、ご確認のほどよろしくお願い申し上げます。

---

笠間和喜
iGroup Japan
kazuki@igroupjapan.com
