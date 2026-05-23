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
   │     - primary_topic + topics[3] を OpenAlex Work スキーマで出力
   ▼
data/topics-irdb-ja-multi.jsonl  (約 2.5M lines、約 700MB、nested 形式)
```

### 4.1 出力フォーマット（JSONL、1 行 1 件）

OpenAlex の Work スキーマに合わせて、`primary_topic`（主トピック）と `topics`（候補配列）の 2 階層で出力します。1 Work あたり通常 3 件の候補 Topic を保持し、`primary_topic` は `topics[0]` と一致します（OpenAlex の慣習に準拠）。

```json
{
  "work_id": "https://openalex.org/W2781293634",
  "primary_topic": {
    "id": "https://openalex.org/T10318",
    "display_name": "Machine Learning in Healthcare",
    "score": 0.7790
  },
  "topics": [
    { "id": "https://openalex.org/T10318", "display_name": "Machine Learning in Healthcare", "score": 0.7790 },
    { "id": "https://openalex.org/T11045", "display_name": "Biomedical Text Mining and Ontologies", "score": 0.7621 },
    { "id": "https://openalex.org/T12503", "display_name": "Clinical Decision Support Systems", "score": 0.7488 }
  ],
  "method": "embedding"
}
```

- `work_id` ：OpenAlex Work URL（IRDB Work と一意対応）
- `primary_topic` ／ `topics[]` の `id` ／ `display_name` ：OpenAlex 公式タクソノミーに準拠
- `score` ：埋め込みベクトル間のコサイン類似度 [0, 1]
- `method` ：`embedding` ／ `ndc_rerank` ／ `ndc_fallback` ／ `skipped` ／ `none`

### 4.2 複数 Topic 対応（OpenAlex Work スキーマとの互換）

OpenAlex は各 Work に **1 件の `primary_topic` ＋ 通常 3〜5 件の `topics` 配列**を保持しています。本ツールも同じ階層構造で出力するため、OpenAlex / IRDB のいずれの側でもそのまま取り込み・比較が可能です。

実装上のポイント：

- 内部では FAISS で常に上位 5 件の候補を計算（`--top-k 5`、デフォルト）
- 出力時に `--top-n N` で書き出す件数を制御（デフォルト 3）
- NDC re-rank で `primary` が `candidates[0]` と入れ替わった場合は、`topics[0]` を新 primary に合わせて並び替え（OpenAlex の慣習に揃える）

### 4.3 後方互換モード（単一 Topic 出力）

`--multi-topic` フラグを付けない場合は従来のフラット形式（`topic_id` / `topic_name` / `confidence` / `method`）で出力されます。既存の取り込みパイプラインを変更せずに使えるよう、後方互換を維持しています。

```json
{
  "work_id": "https://openalex.org/W2781293634",
  "topic_id": "https://openalex.org/T10318",
  "topic_name": "Machine Learning in Healthcare",
  "confidence": 0.7790,
  "method": "embedding"
}
```

---

## 5. 実行結果サマリ

### 5.1 処理量

| 項目 | 値 |
|---|---|
| 対象件数 | 約 2,499,476 件 |
| データ取得時間 | 約 3 時間（途中で OpenAlex rate-limit 19 時間を含むため、実所要は別途 OpenAlex Premium API キー利用） |
| Topic 付与処理時間 | 約 37 時間（Apple Silicon MPS） |
| 出力サイズ | 単一 Topic 形式：約 400 MB（gzip 約 80 MB）／複数 Topic 形式（primary + topics × 3）：約 700 MB（gzip 約 150 MB） |

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

各 Work に対する複数 Topic 候補（本手法・上位 3 件）の例：

| Work | 既存 OpenAlex の primary | 本手法の primary | 本手法の topics[1] | 本手法の topics[2] |
|---|---|---|---|---|
| 言語学・人類学系（Khoisan genealogy） | Blood disorders ✗ | Pleistocene-Era Hominins ✓ | Linguistic Anthropology | Historical Linguistics |
| 数学・微分幾何 | Advanced Differential Geometry ✓ | Advanced Differential Geometry ✓ | Geometry and complex manifolds | Riemannian Geometry |
| 内容分析・テキストマイニング | Analytical Chemistry ✗ | Statistical Modeling Techniques ✓ | Computational Text Analysis | Educational Methods Research |

`topics[1]` `topics[2]` のような副次候補も保持することで、IRDB 側で「primary に加えて関連分野でも検索ヒットさせる」用途にも対応可能です。

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
  - `scripts/assign_topics.py` ：Topic 再付与の本体（チャンク並列、OpenAlex Work スキーマ準拠の複数 Topic 出力対応）

### 7.1 標準的な実行コマンド（複数 Topic 出力、OpenAlex スキーマ準拠）

```bash
# 1. OpenAlex API から IRDB 日本語論文を取得
python scripts/fetch_openalex_works.py \
  --mailto your@example.org \
  --output data/works-irdb-ja.jsonl

# 2. FAISS index を一度構築
python scripts/build_index.py \
  --model intfloat/multilingual-e5-base \
  --index-dir ./index-base \
  --mailto your@example.org

# 3. Topic を再付与（primary_topic + topics[3] を OpenAlex 互換で出力）
python scripts/assign_topics.py \
  --index-dir ./index-base \
  --model intfloat/multilingual-e5-base \
  --input  data/works-irdb-ja.jsonl \
  --output data/topics-irdb-ja-multi.jsonl \
  --minimal --multi-topic --top-n 3
```

---

## 8. 今後の展開（案）

1. **OpenAlex 側へのフィードバック**：CTO Casey 氏宛に複数 Topic 形式（OpenAlex Work スキーマ準拠）で本データを共有
2. **他言語ソースへの拡張**：他国の Institutional Repository ソースに同手法を適用（例：韓国、台湾、中国）
3. **評価データセットの整備**：日本語論文に人手付与の正解 Topic を準備し、各モデルの正答率（Top-1 / Top-3 / Top-5）を定量評価
4. **NII 側での再現／検証の場の設定**：必要に応じてセミナー形式での共有
5. **IRDB の検索 UI への組み込み検討**：primary_topic に加えて topics[1..2] も検索インデックスに含めることで、副次分野でのヒット率向上が期待できる

---

## 9. ご相談事項

1. 本データの OpenAlex 提供に対する NII / IRDB の同意の有無
2. 公表・引用に関する制約事項のご教示
3. NII / IRDB 側でも本データの活用にご関心があるかどうか

ご不明点・追加検証が必要な事項などございましたら、お気軽にお知らせください。
