# 武田先生宛メール（比較表追加ご報告）

> Gmail / Outlook 等にコピペしてご利用ください。

---

**件名：** Re: IRDB 日本語論文への OpenAlex Topic 再付与 — 改善比較表の追加ご報告

---

武田先生

お世話になっております。
iGroup Japan の笠間でございます。

先日お送りいたしました信頼度スコア深掘り分析に加え、**既存 OpenAlex の付与結果と本手法の付与結果を並べた比較表**を作成いたしましたので、追加でご報告申し上げます（添付：`comparison-ja.pdf`）。

## 比較結果のポイント

日本語タイトルを持つ論文 2,256,913 件の中から 10 件を無作為抽出し、既存 OpenAlex の Topic と本手法の Topic を比較しました。

**10 件すべてで primary_topic が変更**されました。特に顕著な例を以下に示します。

| 論文タイトル | 既存 OpenAlex | 本手法 |
|---|---|---|
| 舌咽神経痛・微小血管減圧術 | Military Technology and Strategies ❌ | Trigeminal Neuralgia and Treatments ✅ |
| 急性上気道狭窄・気管切開 | Military Technology and Strategies ❌ | Respiratory Support and Mechanisms ✅ |
| タスクスケジューリング技法 | Military Technology and Strategies ❌ | Scheduling and Timetabling Solutions ✅ |
| 高齢期の整理収納研究 | Military Technology and Strategies ❌ | Migration, Aging, and Tourism Studies ✅ |
| ハクサイの葉面積研究 | Military Technology and Strategies ❌ | Plant Reproductive Biology ✅ |
| 組立材ブレースの座屈解析 | Hermeneutics and Narrative Identity ❌ | Structural Behavior of Reinforced Concrete ✅ |

既存の OpenAlex では、医学・工学・農学・生活科学の論文の多くが「Military Technology and Strategies」や「Hermeneutics and Narrative Identity」などの**全く無関係なトピック**に分類されており、日本語論文に対する系統的な誤動作が明確に確認できました。

本手法ではいずれも**内容に即したトピック**が付与されており、改善効果が具体的に示せたと考えております。

## 現在の添付資料一覧

1. `technical-memo-for-Prof_takeda.pdf` — 技術メモ（モデル選定・パイプライン）
2. `quality-report-full.pdf` — 品質評価レポート（全 249 万件）
3. `deep-analysis.pdf` — 信頼度スコア深掘り分析
4. `comparison-ja.pdf` — 既存 OpenAlex vs 本手法 比較表（本メール添付）

引き続き、本データの OpenAlex への提供・共有についてご意見を伺えますと幸いです。

お忙しいところ恐縮ですが、どうぞよろしくお願い申し上げます。

---

笠間和喜
iGroup Japan
kazuki@igroupjapan.com
