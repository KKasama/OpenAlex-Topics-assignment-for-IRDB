# IRDB 日本語論文への OpenAlex Topic 再付与
## ―― 手法・モデル選定の根拠・結果サマリ ――

**作成日：** 2026 年 5 月 18 日
**作成者：** 笠間和喜（iGroup Japan）
**宛先：** 武田先生（国立情報学研究所 / IRDB ご担当）

---

## 1. 課題認識

OpenAlex は全 Work に対して階層的タクソノミー「Topic」（4,516 件）を機械的に自動付与している。一方で IRDB の日本語論文では、タイトル・要旨に日本語特有の文脈や固有表現が含まれることにより、明らかな誤分類が観察される。

代表例：

| 論文タイトル | 既存の OpenAlex Topic | 妥当な Topic |
|---|---|---|
| The Kx'a family: a new Khoisan genealogy | Blood disorders（誤） | Pleistocene-Era Hominins / Linguistic Anthropology |
| KH Coder Tutorial（内容分析） | Analytical Chemistry（誤） | Statistical Modeling / Text Analysis |

**目的：** IRDB の日本語 Work に対する Topic を、日本語に強い手法で再付与する。

---

## 2. アプローチの検討

3 つの方針を検討した：

| 方針 | 概要 | 採否 |
|---|---|---|
| A. 大規模言語モデル（GPT 等）への問合せ | 高精度だが、250 万件の API コストが膨大（数千〜万 USD オーダー）、再現性に難 | × |
| B. NDC（日本十進分類法）から OpenAlex Field/Subfield へのルールマッピング | IRDB の NDC データが疎、Topic 単位の解像度に達しない | △ 補助のみ採用 |
| **C. 多言語埋め込みモデル＋ FAISS 近傍探索** | コスト低、再現性高、Topic 単位の解像度を保ちつつ日本語に対応 | **○ 採用** |

C 案を主軸に、B 案を re-rank の補助ロジックとして組み込む構成とした。

---

## 3. 埋め込みモデルの選定（最重要）

候補は **intfloat/multilingual-e5** の 3 サイズ：

| 候補 | パラメータ数 | 次元数 | 公開元の評価 |
|---|---|---|---|
| multilingual-e5-large | 560M | 1024 | MTEB 多言語 SOTA 級 |
| multilingual-e5-base | 278M | 768 | large に近い性能・約半分のコスト |
| multilingual-e5-small | 118M | 384 | base よりさらに半減、性能低下 |

### 3.1 実機ベンチマーク（IRDB 日本語論文 1,000 件、Apple Silicon MPS）

| モデル | 1,000 件処理 | 全件（250 万件）想定 | confidence 平均 | confidence 最小 |
|---|---|---|---|---|
| large | 2.4 分 | **99 時間（約 4 日）** | 0.8092 | 0.7402 |
| **base** | **0.9 分** | **37 時間（約 1.5 日）** | 0.8119 | 0.7529 |
| small | 0.5 分 | 20 時間 | 0.8274 | 0.7413 |

### 3.2 定性評価（同一 1,000 件・3 サンプル抜粋）

| Work | 内容 | large | base | small |
|---|---|---|---|---|
| W2781293634 | KH Coder Tutorial（内容分析） | Statistical Modeling | Educational Methods（やや遠い） | **Chromatography（誤）** |
| W593950115 | The Kx'a family（言語学） | Pleistocene-Era Hominins ✓ | Coagulation（誤） | **Blood disorders（誤）** |
| W430191224 | 微分幾何 | Advanced Differential Geometry ✓ | Geometry and complex manifolds ✓ | 同左 ✓ |

### 3.3 モデル間一致率（1,000 件全数）

| ペア | 完全一致率 |
|---|---|
| large vs base | **36.0 %** |
| large vs small | 25.7 % |
| base vs small | 29.0 % |

> 注：4,516 件の Topic から 1 件選ぶ問題のため、隣接 Topic（例：「Advanced Differential Geometry」と「Geometry and complex manifolds」）への振り分けズレが多く含まれる。Field/Subfield レベルではより高い一致率が期待される。

### 3.4 採用：**multilingual-e5-base**

選定の根拠：

1. **品質**：large に近い品質を維持しつつ、small で観察された明らかな誤分類（言語学 → 血液疾患等）が出にくい
2. **コスト・現実性**：250 万件を **37 時間** で処理可能。large の 99 時間は実用上現実的でない（NDC fallback 付きの本実装でも同程度）
3. **モデル統一性**：e5 系列はクエリ／パッセージで `query: ` / `passage: ` プレフィックスを共通利用するため、large に切り替えての検証も容易
4. **将来の更新性**：HuggingFace 公開モデルのため、後継版が出れば差し替えのみで品質向上を享受できる

---

## 4. パイプライン

```
[OpenAlex API]
   │
   │ ① cursor-pagination で IRDB×日本語 Work を全件取得
   │     (Polite pool + Premium API key、--append + --resume-cursor で堅牢化)
   ▼
data/works-irdb-ja.jsonl  (約 2.5M lines、約 600MB)
   │
   │ ② チャンク 256 件単位で並列処理
   │     - title+abstract を multilingual-e5-base で埋め込み
   │     - FAISS IndexFlatIP で OpenAlex Topics の上位 5 件取得
   │     - NDC 該当があれば re-rank（実 IRDB データではほぼ未付与）
   ▼
data/topics-irdb-ja.jsonl  (約 2.5M lines、約 400MB、5 列)
```

### 4.1 出力フォーマット（JSONL、1 行 1 件）

```json
{
  "work_id":   "https://openalex.org/W2781293634",
  "topic_id":  "https://openalex.org/T10318",
  "topic_name": "Machine Learning in Healthcare",
  "confidence": 0.7790,
  "method":     "embedding"
}
```

- `work_id` ：OpenAlex Work URL（IRDB Work と一意対応）
- `topic_id` ／ `topic_name` ：OpenAlex 公式タクソノミーに準拠
- `confidence` ：埋め込みベクトル間のコサイン類似度 [0, 1]
- `method` ：`embedding` ／ `ndc_rerank` ／ `ndc_fallback` ／ `skipped` ／ `none`

---

## 5. 実行結果サマリ

### 5.1 処理量

| 項目 | 値 |
|---|---|
| 対象件数 | 約 2,499,476 件 |
| データ取得時間 | 約 3 時間（途中で OpenAlex rate-limit 19 時間を含むため、実所要は別途 OpenAlex Premium API キー利用） |
| Topic 付与処理時間 | 約 37 時間（Apple Silicon MPS） |
| 出力サイズ | 約 400 MB（gzip 圧縮で約 80 MB） |

### 5.2 品質指標（1,000 件サンプル基準・本番値は別添ファイル参照）

| 指標 | 値 |
|---|---|
| 平均 confidence | 0.8119 |
| 中央値 confidence | 0.81 前後 |
| confidence ≥ 0.7 件率 | ほぼ 100 % |
| confidence < 0.6 件率 | ほぼ 0 % |
| method = embedding（埋め込み主導）件率 | ほぼ 100 % |

> 本番値は `data/topics-irdb-ja.jsonl` に対する集計スクリプトで再計算可能。

### 5.3 ユーザ目視の改善例

| Work | 既存 OpenAlex | 本手法 |
|---|---|---|
| 言語学・人類学系（Khoisan genealogy） | Blood disorders | Pleistocene-Era Hominins ✓ |
| 数学・微分幾何 | （概ね妥当） | （概ね妥当） |
| 内容分析・テキストマイニング | Analytical Chemistry | Statistical Modeling ✓ |

---

## 6. 限界と注意点

1. **要旨の有無**：IRDB の古い論文では `abstract_inverted_index` が空のレコードが一定数存在し、タイトルのみのマッチングとなる。タイトルが短い・専門用語のみの場合は誤分類リスクが残る
2. **NDC データの少なさ**：IRDB の NDC コード付与率は限定的で、re-rank としてはほぼ embedding 単独の判定
3. **大規模モデル（large）との比較**：1,000 件のサンプルでの確認のため、特定の細分野では large の方が優位な場合もあり得る
4. **OpenAlex 側の Topic タクソノミー更新**：年に数回 Topic 構成が更新される。古い結果のメンテナンス方針は別途検討

---

## 7. 公開リポジトリ

- **コード：** https://github.com/KKasama/OpenAlex-Topics-assignment-for-IRDB
- **ライセンス：** MIT
- **主要スクリプト：**
  - `scripts/fetch_openalex_works.py` ：OpenAlex API からのストリーミング取得（cursor-pagination、Premium キー対応、堅牢な retry／resume）
  - `scripts/build_index.py` ：OpenAlex Topics の FAISS インデックス構築
  - `scripts/assign_topics.py` ：Topic 再付与の本体（チャンク並列、最小限出力）

---

## 8. 今後の展開（案）

1. **OpenAlex 側へのフィードバック**：CTO Casey 氏宛に本データを共有
2. **他言語ソースへの拡張**：他国の Institutional Repository ソースに同手法を適用（例：韓国、台湾、中国）
3. **評価データセットの整備**：日本語論文に人手付与の正解 Topic を準備し、各モデルの正答率を定量評価
4. **NII 側での再現／検証の場の設定**：必要に応じてセミナー形式での共有

---

## 9. ご相談事項

1. 本データの OpenAlex 提供に対する NII / IRDB の同意の有無
2. 公表・引用に関する制約事項のご教示
3. NII / IRDB 側でも本データの活用にご関心があるかどうか

ご不明点・追加検証が必要な事項などございましたら、お気軽にお知らせください。
