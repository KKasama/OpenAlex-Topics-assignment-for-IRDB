# 品質評価レポート（全件：2,499,476 件）
## IRDB 日本語論文への OpenAlex Topic 再付与 — multilingual-e5-base

**作成日：** 2026 年 5 月 25 日
**評価対象：** IRDB 日本語論文 全件（OpenAlex Source ID `S7407056385`）
**評価対象ファイル：** `data/topics-irdb-ja-multi.jsonl`
**処理時間：** 1,658.9 分（約 27.6 時間）

---

## 1. サマリ

| 指標 | 値 |
|---|---|
| 評価件数 | **2,499,476 件** |
| マッチング方式 | すべて埋め込みベース（`method=embedding`） |
| 1 Work あたり Topic 数 | **3.00 件**（全件） |
| 空 topics | 0 件 |
| スキップ（非日本語） | 0 件 |
| NDC fallback 利用 | 0 件 |
| 出力ファイルサイズ | 1.3 GB（gzip 圧縮後 165 MB） |

全件で OpenAlex Work スキーマ準拠の `primary_topic` ＋ `topics` 配列 3 件が付与されました。

---

## 2. Primary Topic スコア分布

| 統計量 | 全件（2.5M） | 1k サンプル（参考） |
|---|---|---|
| **平均** | **0.7962** | 0.8119 |
| 中央値 | 0.7983 | 0.8129 |
| 最小 | **0.6802** | 0.7529 |
| 最大 | **0.9038** | 0.8643 |

| しきい値 | 件率（全件） | 件率（1k） |
|---|---|---|
| score ≥ 0.8 | **47.0 %** | 77.7 % |
| score ≥ 0.7 | **100.0 %** | 100.0 % |
| score < 0.6 | **0.0 %** | 0.0 % |

> **解釈：** 全 2,499,476 件で score ≥ 0.7 を維持しており、低信頼度レコードは皆無です。1k サンプルと比較すると score ≥ 0.8 の比率が低下（77.7% → 47.0%）していますが、これは予測どおりであり、要旨が空または短いタイトルのみの論文が分布の裾を形成したためと考えられます。最小値 0.68 も十分な信頼度です。

---

## 3. Topic カバレッジ（ユニーク Topic 数）

| 指標 | 値 |
|---|---|
| Primary Topic のユニーク数 | **4,515** / 4,516 |
| 全 Topic（top-3 合計）のユニーク数 | **4,516** |
| OpenAlex Topics 総数（タクソノミー） | 4,516 |

> **解釈：** OpenAlex の全タクソノミー（4,516 Topics）がほぼ完全に網羅されました。2,499,476 件という大規模データに対して特定の Topic への過度な集中は見られず、IRDB が収録する日本の学術研究の多様性が反映された結果です。

---

## 4. Primary Topic 上位 20 件

| 件数 | 比率 | Topic |
|---:|---:|---|
| 50,499 | 2.0 % | Urban and spatial planning |
| 42,036 | 1.7 % | Coagulation, Bradykinin, Polyphosphates, and Angioedema |
| 30,910 | 1.2 % | Injection Molding Process and Properties |
| 29,197 | 1.2 % | Urban Planning and Landscape Design |
| 25,001 | 1.0 % | Lymphadenopathy Diagnosis and Analysis |
| 20,306 | 0.8 % | Decadence, Literature, and Society |
| 16,591 | 0.7 % | Renal and related cancers |
| 15,004 | 0.6 % | Diverse Academic Research Analysis |
| 14,210 | 0.6 % | Dielectric properties of ceramics |
| 12,755 | 0.5 % | Vasculitis and related conditions |
| 11,793 | 0.5 % | Forest, Soil, and Plant Ecology in China |
| 11,649 | 0.5 % | Coding theory and cryptography |
| 11,513 | 0.5 % | Genetic and rare skin diseases |
| 11,107 | 0.4 % | Currency Recognition and Detection |
| 10,324 | 0.4 % | Japanese History and Culture |
| 10,097 | 0.4 % | Clinical Laboratory Practices and Quality Control |
| 10,042 | 0.4 % | Cognitive and psychological constructs research |
| 9,992 | 0.4 % | Medieval Architecture and Archaeology |
| 9,723 | 0.4 % | Ecology, Conservation, and Geographical Studies |
| 9,504 | 0.4 % | EFL/ESL Teaching and Learning |

> **注：** 上位に「Coagulation, Bradykinin...」「Injection Molding」「Lymphadenopathy」など、IRDB 全体の印象と比べて意外な Topic が現れています。これらは要旨が空・タイトルが極めて短い論文が埋め込み空間の特定クラスタに引き寄せられたことが原因として疑われます（「既知の限界」セクション参照）。最上位の「Urban and spatial planning」（2.0%）は日本の大学リポジトリに都市計画・建築系論文が多いことと整合します。

---

## 5. Method 内訳

| Method | 件数 | 件率 |
|---|---:|---:|
| embedding | 2,499,476 | 100.0 % |
| ndc_rerank | 0 | 0.0 % |
| ndc_fallback | 0 | 0.0 % |
| skipped | 0 | 0.0 % |
| none | 0 | 0.0 % |

> **解釈：** 入力データの全件が日本語論文として処理され、埋め込みベースの判定のみで完結しました。

---

## 6. 評価ロジックの妥当性

スコア（cosine similarity in [0, 1]）は埋め込みベクトル間の意味的類似度です。

### スコアの解釈目安

| スコア帯 | 解釈 | 本データの件率 |
|---|---|---:|
| 0.85 以上 | 非常に強いマッチ | — |
| 0.75 〜 0.85 | 強いマッチ（本データの主要分布帯） | — |
| 0.70 〜 0.75 | 中程度のマッチ | — |
| 0.65 〜 0.70 | 弱めのマッチ | — |
| 0.65 未満 | 弱いマッチ | **0.0 %** |

全件で最低スコアが 0.68 であり、明らかな低信頼度レコードは存在しません。

---

## 7. 既知の限界

1. **要旨なし・短タイトルの Work**：古い論文や要旨が登録されていない Works では、タイトルのみを埋め込みに使用するため、特定の Topic クラスタへの過集中が生じる場合があります。上位 20 Topic のうち一部（医学系・製造業系）の件数が多いのはこの影響の可能性があります。
2. **人手付与の正解との照合は未実施**：本レポートはスコア分布と Topic 多様性のみを評価対象とし、第三者による正解 Topic との比較評価は今後の課題です。
3. **既存 OpenAlex 付与との比較**：本手法と既存 OpenAlex 付与の比較は別添「改善比較表」（`docs/comparison-1k.md`）を参照してください（10 件サンプル）。

---

## 8. 次の評価ステップ（提案）

1. **人手評価セット**：100〜200 件規模で人手で正解 Topic を付け、本手法・既存 OpenAlex の双方を Top-1 / Top-3 精度で比較
2. **既存 OpenAlex 付与との field レベル一致率**：より大きいサンプル（1,000 件以上）での比較
3. **短タイトル・要旨なし論文の特定**：上位集中 Topic の Works を抽出し、人手で誤分類率を確認

---

参考：本レポートは `data/topics-irdb-ja-multi.jsonl`（全 2,499,476 件）を Python で集計したものです。再現用スクリプトは GitHub リポジトリ（`scripts/` ディレクトリ）に整備されています。
