# 武田先生宛メール本文（下書き）

> 本文を Gmail / Outlook 等にコピペしてご利用ください。
> 角括弧 `[...]` は実際の値に差し替えてください。

---

**件名：** IRDB 日本語論文への OpenAlex Topic 再付与結果のご報告とご相談

---

武田先生

ご無沙汰しております。
iGroup Japan の笠間と申します。

このたび、IRDB に収録されている日本語論文に対する OpenAlex 上の Topic 自動付与について、別手法による再付与を試行いたしました。結果を先生にご確認いただいた上で、可能であれば OpenAlex（CTO の Casey 氏）にも共有させていただきたく、ご相談させてください。

## 背景

OpenAlex は全ての Work（論文）に対して 4,500 件規模のタクソノミー「Topic」を自動付与していますが、IRDB の日本語論文では誤分類が一定数見受けられる状況でした。原因は OpenAlex 側の自動付与モデルが日本語表現の文脈をうまく捉えきれていないことにあると推測しております（例：言語学の論文タイトル "The Kx'a family: a new Khoisan genealogy" が血液関連 Topic に分類される等）。

## 実施内容

- 対象：IRDB（OpenAlex Source ID `S7407056385`）の日本語論文 **約 2,499,476 件**
- 手法：日本語に強い多言語埋め込みモデル `intfloat/multilingual-e5-base` でタイトル＋要旨をベクトル化し、OpenAlex の Topics（4,516 件）に対して FAISS による近傍探索でマッチング
- 出力：JSONL 形式・5 列（`work_id`, `topic_id`, `topic_name`, `confidence`, `method`）

## ご相談事項

1. 本結果データの OpenAlex への提供について、NII・IRDB の観点からご懸念がないかご確認いただきたく
2. 公表・共有に関する制約事項のご教示
3. （差し支えなければ）NII・IRDB 側でも本データに関心がおありか

## 添付資料

本件の方法論、特に「**なぜこのモデルを選定したか**」の根拠ベンチマークを含む技術メモを添付しております（`technical-memo-for-takeda.md` ／ `technical-memo-for-takeda.pdf`）。ご一読いただけますと幸いです。

## ソースコードについて

実装は MIT ライセンスで GitHub に公開しております：
https://github.com/KKasama/OpenAlex-Topics-assignment-for-IRDB

再現性の担保と、必要であれば NII 側でも追試いただけるよう設計しております。

---

お忙しいところ恐縮ですが、ご検討のほどよろしくお願い申し上げます。

笠間和喜
iGroup Japan
kazuki@igroupjapan.com
