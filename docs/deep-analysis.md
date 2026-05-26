# 信頼度スコア深掘り分析レポート
## IRDB 日本語論文 OpenAlex Topic 再付与 — multilingual-e5-base

**作成日：** 2026 年 5 月 26 日  
**対象件数：** 2,499,476 件  
**タイトル長短閾値：** 30 文字

---


## 1a. Primary Topic 上位 20 件：階層情報とスコア分布

> 各 Topic の OpenAlex 階層（Domain / Field / Subfield）とスコア統計量（件数・平均・中央値・標準偏差・最小・最大）。

| 件数 | Topic | Domain | Field | Subfield | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 50,499 | Urban and spatial planning | Physical Sciences | Environmental Science | Nature and Landscape Conservation | 0.7863 | 0.7839 | 0.0212 | 0.6934 | 0.8748 |
| 42,036 | Coagulation, Bradykinin, Polyphosphates, and Angioedema | Health Sciences | Medicine | Genetics | 0.7922 | 0.7932 | 0.0251 | 0.7090 | 0.8787 |
| 30,910 | Injection Molding Process and Properties | Physical Sciences | Engineering | Mechanical Engineering | 0.7979 | 0.8008 | 0.0180 | 0.7181 | 0.8640 |
| 29,197 | Urban Planning and Landscape Design | Physical Sciences | Environmental Science | Management, Monitoring, Policy and Law | 0.7723 | 0.7719 | 0.0166 | 0.6962 | 0.8507 |
| 25,001 | Lymphadenopathy Diagnosis and Analysis | Health Sciences | Medicine | Surgery | 0.7892 | 0.7914 | 0.0256 | 0.7005 | 0.8631 |
| 20,306 | Decadence, Literature, and Society | Social Sciences | Social Sciences | Sociology and Political Science | 0.7719 | 0.7714 | 0.0156 | 0.6997 | 0.8662 |
| 16,591 | Renal and related cancers | Life Sciences | Biochemistry, Genetics and Molecular Biology | Molecular Biology | 0.7866 | 0.7806 | 0.0175 | 0.6904 | 0.8619 |
| 15,004 | Diverse Academic Research Analysis | Social Sciences | Social Sciences | Sociology and Political Science | 0.7886 | 0.7895 | 0.0156 | 0.7091 | 0.8373 |
| 14,210 | Dielectric properties of ceramics | Physical Sciences | Materials Science | Materials Chemistry | 0.7967 | 0.8025 | 0.0216 | 0.7172 | 0.8661 |
| 12,755 | Vasculitis and related conditions | Health Sciences | Medicine | Pulmonary and Respiratory Medicine | 0.7936 | 0.8025 | 0.0279 | 0.7128 | 0.8979 |
| 11,793 | Forest, Soil, and Plant Ecology in China | Social Sciences | Social Sciences | Education | 0.7974 | 0.7998 | 0.0198 | 0.7264 | 0.8518 |
| 11,649 | Coding theory and cryptography | Physical Sciences | Computer Science | Artificial Intelligence | 0.7856 | 0.7851 | 0.0198 | 0.7218 | 0.8648 |
| 11,513 | Genetic and rare skin diseases. | Life Sciences | Biochemistry, Genetics and Molecular Biology | Genetics | 0.7954 | 0.8008 | 0.0247 | 0.7138 | 0.8560 |
| 11,107 | Currency Recognition and Detection | Physical Sciences | Computer Science | Computer Vision and Pattern Recognition | 0.7797 | 0.7799 | 0.0082 | 0.7136 | 0.8278 |
| 10,324 | Japanese History and Culture | Social Sciences | Social Sciences | Cultural Studies | 0.7837 | 0.7841 | 0.0177 | 0.7033 | 0.8494 |
| 10,097 | Clinical Laboratory Practices and Quality Control | Health Sciences | Medicine | Physiology | 0.7971 | 0.7985 | 0.0165 | 0.7185 | 0.8531 |
| 10,042 | Cognitive and psychological constructs research | Social Sciences | Psychology | Social Psychology | 0.7887 | 0.7902 | 0.0184 | 0.6949 | 0.8474 |
| 9,992 | Medieval Architecture and Archaeology | Social Sciences | Arts and Humanities | Archeology | 0.7744 | 0.7774 | 0.0088 | 0.7112 | 0.8317 |
| 9,723 | Ecology, Conservation, and Geographical Studies | Physical Sciences | Environmental Science | Nature and Landscape Conservation | 0.8069 | 0.8112 | 0.0156 | 0.7268 | 0.8531 |
| 9,504 | EFL/ESL Teaching and Learning | Social Sciences | Arts and Humanities | Language and Linguistics | 0.8059 | 0.8061 | 0.0169 | 0.7398 | 0.8721 |


## 1b. Primary Topic 下位 20 件：階層情報とスコア分布

> 各 Topic の OpenAlex 階層（Domain / Field / Subfield）とスコア統計量（件数・平均・中央値・標準偏差・最小・最大）。

| 件数 | Topic | Domain | Field | Subfield | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | Scientific Research Methodologies and Applications | Physical Sciences | Environmental Science | Water Science and Technology | 0.7761 | 0.7761 | 0.0000 | 0.7761 | 0.7761 |
| 1 | Graphene and Nanomaterials Applications | Physical Sciences | Engineering | Biomedical Engineering | 0.8002 | 0.8002 | 0.0000 | 0.8002 | 0.8002 |
| 2 | Nanowire Synthesis and Applications | Physical Sciences | Engineering | Biomedical Engineering | 0.8291 | 0.8291 | 0.0091 | 0.8226 | 0.8355 |
| 2 | Agricultural and Biological Research | Life Sciences | Agricultural and Biological Sciences | Food Science | 0.8344 | 0.8344 | 0.0317 | 0.8120 | 0.8568 |
| 2 | Bioeconomy and Sustainability Development | Life Sciences | Agricultural and Biological Sciences | General Agricultural and Biological Sciences | 0.8253 | 0.8253 | 0.0056 | 0.8213 | 0.8292 |
| 2 | Race, Genetics, and Society | Life Sciences | Biochemistry, Genetics and Molecular Biology | Genetics | 0.8092 | 0.8092 | 0.0288 | 0.7888 | 0.8296 |
| 2 | Cultural, Linguistic, Economic Studies | Social Sciences | Social Sciences | General Social Sciences | 0.7933 | 0.7933 | 0.0240 | 0.7763 | 0.8102 |
| 2 | Supercapacitor Materials and Fabrication | Physical Sciences | Materials Science | Electronic, Optical and Magnetic Materials | 0.8396 | 0.8396 | 0.0039 | 0.8368 | 0.8423 |
| 3 | Sociology and Education in Brazil | Social Sciences | Social Sciences | Sociology and Political Science | 0.7909 | 0.7892 | 0.0080 | 0.7839 | 0.7996 |
| 3 | Wireless Sensor Networks for Data Analysis | Physical Sciences | Computer Science | Computer Networks and Communications | 0.8366 | 0.8340 | 0.0226 | 0.8154 | 0.8603 |
| 3 | Water and Wastewater Treatment | Physical Sciences | Engineering | Computational Mechanics | 0.8177 | 0.8042 | 0.0312 | 0.7956 | 0.8534 |
| 3 | Quantum Dots Synthesis And Properties | Physical Sciences | Materials Science | Materials Chemistry | 0.8151 | 0.8240 | 0.0179 | 0.7945 | 0.8268 |
| 3 | Structural mechanics and materials | Physical Sciences | Materials Science | Materials Chemistry | 0.7968 | 0.8100 | 0.0327 | 0.7596 | 0.8208 |
| 3 | Technology and Security Systems | Physical Sciences | Computer Science | Information Systems | 0.8197 | 0.8249 | 0.0101 | 0.8080 | 0.8261 |
| 3 | Philosophy and Phenomenology Studies | Social Sciences | Social Sciences | General Social Sciences | 0.8319 | 0.8347 | 0.0288 | 0.8018 | 0.8592 |
| 3 | Plant nutrient uptake and metabolism | Life Sciences | Agricultural and Biological Sciences | Plant Science | 0.8197 | 0.8159 | 0.0111 | 0.8111 | 0.8322 |
| 3 | Leech Biology and Applications | Health Sciences | Medicine | Pharmacology | 0.8265 | 0.8234 | 0.0072 | 0.8213 | 0.8347 |
| 4 | Phytochemical compounds biological activities | Life Sciences | Biochemistry, Genetics and Molecular Biology | Molecular Biology | 0.8120 | 0.8058 | 0.0234 | 0.7917 | 0.8448 |
| 4 | Nanoparticles: synthesis and applications | Physical Sciences | Materials Science | Materials Chemistry | 0.8324 | 0.8354 | 0.0224 | 0.8026 | 0.8562 |
| 4 | Covalent Organic Framework Applications | Physical Sciences | Materials Science | Materials Chemistry | 0.8155 | 0.8148 | 0.0037 | 0.8117 | 0.8204 |


## 2. SubField 単位のスコア分布（件数上位 30 SubField）

> SubField（OpenAlex タクソノミー第 3 階層）ごとのスコア統計量。件数上位 30 を表示。

| 件数 | SubField | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |
|---:|---|---:|---:|---:|---:|---:|
| 140,698 | Sociology and Political Science | 0.7884 | 0.7885 | 0.0201 | 0.6997 | 0.8820 |
| 117,821 | Education | 0.8004 | 0.8011 | 0.0182 | 0.7075 | 0.8885 |
| 72,353 | Surgery | 0.8016 | 0.8080 | 0.0251 | 0.7005 | 0.8977 |
| 71,318 | Genetics | 0.7944 | 0.7990 | 0.0254 | 0.7007 | 0.8787 |
| 64,035 | Nature and Landscape Conservation | 0.7901 | 0.7904 | 0.0216 | 0.6934 | 0.8748 |
| 56,819 | Political Science and International Relations | 0.7898 | 0.7899 | 0.0188 | 0.6923 | 0.8782 |
| 55,138 | Molecular Biology | 0.8014 | 0.8050 | 0.0225 | 0.6904 | 0.8965 |
| 52,507 | Social Psychology | 0.7948 | 0.7963 | 0.0205 | 0.6949 | 0.8742 |
| 52,492 | Mechanical Engineering | 0.8008 | 0.8031 | 0.0185 | 0.7170 | 0.8745 |
| 47,468 | Electrical and Electronic Engineering | 0.8004 | 0.8020 | 0.0188 | 0.7017 | 0.8836 |
| 47,286 | Management, Monitoring, Policy and Law | 0.7807 | 0.7788 | 0.0209 | 0.6962 | 0.8756 |
| 43,778 | Economics and Econometrics | 0.7937 | 0.7935 | 0.0183 | 0.6937 | 0.8808 |
| 41,846 | Philosophy | 0.7807 | 0.7803 | 0.0192 | 0.6941 | 0.8674 |
| 39,699 | Literature and Literary Theory | 0.7800 | 0.7791 | 0.0202 | 0.6953 | 0.8765 |
| 36,417 | Artificial Intelligence | 0.7943 | 0.7960 | 0.0206 | 0.7171 | 0.8816 |
| 35,741 | Information Systems | 0.7968 | 0.8006 | 0.0207 | 0.7172 | 0.8667 |
| 34,147 | Cultural Studies | 0.7875 | 0.7879 | 0.0187 | 0.7033 | 0.8696 |
| 33,090 | Public Health, Environmental and Occupational Health | 0.8002 | 0.7989 | 0.0186 | 0.7196 | 0.8817 |
| 32,988 | Pulmonary and Respiratory Medicine | 0.8048 | 0.8117 | 0.0262 | 0.7128 | 0.8979 |
| 30,921 | Materials Chemistry | 0.8039 | 0.8069 | 0.0199 | 0.7117 | 0.8805 |
| 30,496 | Clinical Psychology | 0.7981 | 0.7996 | 0.0208 | 0.7166 | 0.8781 |
| 29,119 | Law | 0.7864 | 0.7865 | 0.0177 | 0.7086 | 0.8661 |
| 28,494 | Plant Science | 0.7912 | 0.7949 | 0.0249 | 0.7072 | 0.8880 |
| 26,785 | Language and Linguistics | 0.8000 | 0.8009 | 0.0185 | 0.7127 | 0.8820 |
| 25,686 | Developmental and Educational Psychology | 0.8041 | 0.8047 | 0.0170 | 0.7123 | 0.8793 |
| 25,437 | Biomedical Engineering | 0.8024 | 0.8052 | 0.0202 | 0.7215 | 0.8860 |
| 23,435 | Civil and Structural Engineering | 0.8041 | 0.8060 | 0.0207 | 0.7226 | 0.8859 |
| 23,228 | Aerospace Engineering | 0.8035 | 0.8048 | 0.0169 | 0.7048 | 0.8734 |
| 22,128 | Archeology | 0.7791 | 0.7774 | 0.0164 | 0.7112 | 0.8631 |
| 21,482 | History | 0.7791 | 0.7792 | 0.0196 | 0.6802 | 0.8680 |


## 3. 入力情報の質によるスコア比較（閾値：タイトル 30 文字）

> 各 Work を「要旨の有無」×「タイトルの長短」の 4 パターンに分けてスコア分布を比較。

| パターン | 要旨 | タイトル | 件数 | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |
|---|:---:|:---:|---:|---:|---:|---:|---:|---:|
| パターン A | あり | 長 (>30字) | 260,647 | 0.8123 | 0.8142 | 0.0178 | 0.7340 | 0.8937 |
| パターン B | あり | 短 (≤30字) | 207,704 | 0.8088 | 0.8111 | 0.0189 | 0.7185 | 0.8965 |
| パターン C | なし | 長 (>30字) | 873,288 | 0.8009 | 0.8026 | 0.0193 | 0.7010 | 0.9038 |
| パターン D | なし | 短 (≤30字) | 1,157,837 | 0.7868 | 0.7874 | 0.0209 | 0.6802 | 0.8921 |

> **解釈のポイント：** 要旨あり・長タイトルのパターン A が最も高スコアになることが期待されます。パターン D（要旨なし・短タイトル）との差が大きい場合、入力情報の質がスコアに有意な影響を与えていることを示します。


## 4. スコア帯の件率（品質レポート補完）

> `quality-report-full.md` で空欄だった「本データの件率」を補完。

| スコア帯 | 解釈 | 件数 | 件率 |
|---|---|---:|---:|
| 0.85 以上 | 非常に強いマッチ | 9,835 | **0.4 %** |
| 0.80〜0.85 | 強いマッチ（上位層） | 1,165,105 | **46.6 %** |
| 0.75〜0.80 | 強いマッチ（主要分布帯） | 1,267,474 | **50.7 %** |
| 0.70〜0.75 | 中程度のマッチ | 57,027 | **2.3 %** |
| 0.65〜0.70 | 弱めのマッチ | 35 | **0.0 %** |
| 0.65 未満 | 弱いマッチ | 0 | **0.0 %** |


## 5. 全件スコア統計（再掲）

| 統計量 | 値 |
|---|---|
| n | 2,499,476 |
| mean | 0.7962 |
| median | 0.7983 |
| std | 0.0220 |
| min | 0.6802 |
| max | 0.9038 |

---

*本レポートは `scripts/deep_analysis.py` により自動生成されました。*