# 佐賀 農地マップ検索 🌾

佐賀県内の圃場の**所在・地番（番地）**を入力すると、航空写真地図上の該当区画に移動する Streamlit アプリ。
農地データは農林水産省 **eMAFF農地ナビ** から取得した GeoJSON（農地ピン / 筆ポリゴン）を読み込んで使う。

## 機能
- 所在・地番・小字での部分一致検索（全角半角・ハイフンゆらぎを吸収）
- 検索結果一覧 → クリックで該当区画へ移動・強調
- Esri 航空写真 / OSM 標準地図の切替
- 農地ピン（地番・地目・面積などの属性ポップアップ）と筆ポリゴンの表示
- 起動時は佐賀市周辺のサンプル圃場を表示

## ローカル実行
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## デプロイ（Streamlit Community Cloud）
1. このリポジトリを GitHub に push
2. https://share.streamlit.io で New app → リポジトリ・ブランチ・`app.py` を指定
3. Deploy

## 実データの入れ方
1. [eMAFF農地ナビ](https://map.maff.go.jp/) を開く
2. 佐賀県内の対象エリアまでズーム（14以上）
3. 上部「ダウンロード」→ 形式 **GeoJSON** を選択
4. 「農地ピン」（地番・面積入り）と必要なら「農地ポリゴン」を取得
5. アプリのアップローダで読み込む

※県・市町村単位の一括ダウンロードは未対応のため、エリアごとに取得する。

## データ出典
- 農地の区画情報（筆ポリゴン）／eMAFF農地ナビ：農林水産省
- 航空写真：Esri World Imagery ／ 標準地図：OpenStreetMap
