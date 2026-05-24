# 品質評価レポート（1,000 件サンプル）
## IRDB 日本語論文への OpenAlex Topic 再付与 — multilingual-e5-base

**作成日：** 2026 年 5 月 18 日
**評価対象：** IRDB 日本語論文 1,000 件（OpenAlex Source ID `S7407056385` から無作為に取得）
**評価対象ファイル：** `data/topics-1k-multi.jsonl`

---

## 1. サマリ

| 指標 | 値 |
|---|---|
| 評価件数 | 1,000 件 |
| マッチング方式 | すべて埋め込みベース（`method=embedding`） |
| 1 Work あたり Topic 数 | **3.00 件**（全件） |
| 空 topics | 0 件 |
| NDC fallback 利用 | 0 件（IRDB の NDC 付与が疎なため） |

全件で OpenAlex Work スキーマ準拠の `primary_topic` ＋ `topics` 配列 3 件が付与されました。

---

## 2. Primary Topic スコア分布

| 統計量 | 値 |
|---|---|
| **平均** | **0.8119** |
| 中央値 | 0.8129 |
| 25 パーセンタイル | 0.8016 |
| 75 パーセンタイル | 0.8238 |
| 最小 | 0.7529 |
| 最大 | 0.8643 |

| しきい値 | 件率 |
|---|---|
| score ≥ 0.8 | **77.7 %** |
| score ≥ 0.7 | **100.0 %** |
| score ≥ 0.6 | 100.0 % |
| score < 0.6 | 0.0 % |

> **解釈：** すべての Work が confidence 0.7 以上、約 78 % が 0.8 以上で付与されており、低信頼度のレコードは観測されませんでした。閾値 0.5 を下回るものは皆無で、NDC fallback への切替も発生していません。

---

## 3. Topic カバレッジ（ユニーク Topic 数）

| 指標 | 値 |
|---|---|
| Primary Topic のユニーク数 | **640** / 1,000 |
| 全 Topic（top-3 合計）のユニーク数 | **1,369** |
| OpenAlex Topics 総数（タクソノミー） | 4,516 |

> **解釈：** 1,000 件の論文に対して 640 種類の primary が選ばれており、特定 Topic への偏りは少ない結果です。top-3 では 1,369 種類に分散しており、複数 Topic 構造が副次分野を含む形で機能していることが確認できます。

---

## 4. Primary Topic 上位 15 件

| 件数 | Topic |
|---:|---|
| 24 | Urban and spatial planning |
| 18 | EFL/ESL Teaching and Learning |
| 14 | Forest, Soil, and Plant Ecology in China |
| 10 | Japanese History and Culture |
| 8 | Geometry and complex manifolds |
| 8 | Approximation Theory and Sequence Spaces |
| 7 | Phonetics and Phonology Research |
| 7 | Coding theory and cryptography |
| 7 | Landslides and related hazards |
| 6 | Swearing, Euphemism, Multilingualism |
| 6 | Syntax, Semantics, Linguistic Variation |
| 6 | Fixed Point Theorems Analysis |
| 6 | Reproductive biology and impacts on aquatic species |
| 6 | Optimization and Variational Analysis |
| 5 | Natural Language Processing Techniques |

> **解釈：** 都市計画、英語教育、林学、日本史、数学、言語学、地学、生物学など、IRDB に登録されている多様な日本語研究の分布を反映しています。特に英語教育（EFL/ESL）の上位ランクインは、日本の大学リポジトリの傾向と整合します。

---

## 5. Method 内訳

| Method | 件数 | 件率 |
|---|---:|---:|
| embedding | 1,000 | 100.0 % |
| ndc_rerank | 0 | 0.0 % |
| ndc_fallback | 0 | 0.0 % |
| skipped | 0 | 0.0 % |
| none | 0 | 0.0 % |

> **解釈：** 入力データの全件が日本語と判定され（`japanese_only` フィルタを通過）、すべて埋め込みベースの判定が機能しました。NDC コードが付与された Work がほぼ無いため、re-rank および fallback は発生していません。

---

## 6. 評価ロジックの妥当性

スコア（cosine similarity in [0, 1]）は埋め込みベクトル間の意味的類似度であり、`primary_topic.score = 0.81` は「論文の意味表現が選択された Topic の代表ベクトルに極めて近い」ことを示します。

### スコアの解釈目安

| スコア帯 | 解釈 |
|---|---|
| 0.85 以上 | 非常に強いマッチ |
| 0.75 〜 0.85 | 強いマッチ（本データの主要分布帯） |
| 0.65 〜 0.75 | 中程度のマッチ（境界事例） |
| 0.65 未満 | 弱いマッチ（本データでは観測されず） |

---

## 7. 既知の限界

1. **抽象不足の Work**：要旨が空または短い古い論文では、タイトルのみでの判定となり、相対的に誤分類リスクが残ります。本サンプルでは全件で score ≥ 0.7 を維持しましたが、本番 2.5M 件では裾の長い分布になる可能性があります。
2. **本サンプルは無作為**：特定分野に絞った評価ではないため、専門分野（医学・工学・人文系）ごとの精度差は別途の評価が必要です。
3. **人手付与の正解との照合は未実施**：本レポートはモデルのスコア分布と Topic 多様性のみを評価対象とし、第三者による正解 Topic との比較評価は今後の課題です。

---

## 8. 次の評価ステップ（提案）

1. **本番 2.5M 件の分布確認**：完了後、本レポートと同じ集計を実施し、低 score 帯の存在を確認
2. **人手評価セット**：100〜200 件規模で人手で正解 Topic を付け、本手法・既存 OpenAlex の双方を Top-1 / Top-3 精度で比較
3. **既存 OpenAlex 付与との一致率**：本手法と既存 OpenAlex 付与の field レベル一致率を測定（別添「改善比較表」を参照）

---

参考：本レポートは `data/topics-1k-multi.jsonl` を入力に Python で集計したものです。再現用スクリプトは GitHub リポジトリ（`scripts/` ディレクトリ）配下に整備予定です。
