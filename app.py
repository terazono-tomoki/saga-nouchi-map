"""
佐賀 農地マップ検索 — 1ページ目：地番検索 / データ読み込み
地番を入力して「検索」を押すと、2ページ目のマップへ移動し該当区画を表示する。
"""
import json

import streamlit as st

from lib import extract_features, rank_hits, sample_geojson

st.set_page_config(page_title="佐賀 農地マップ検索", page_icon="🌾", layout="wide")

MAP_PAGE = "pages/1_🗺️_マップ.py"

# ---------------- 状態 ----------------
if "geojsons" not in st.session_state:
    st.session_state.geojsons = [sample_geojson()]
    st.session_state.data_label = "サンプル：佐賀市周辺のダミー圃場 8件"
if "hits" not in st.session_state:
    st.session_state.hits = []
    st.session_state.query = ""
    st.session_state.current_index = 0

st.title("🌾 佐賀 農地マップ検索")
st.caption(
    "細目書に書かれた**地番**を入力して「検索」を押すと、"
    "該当する圃場の位置がマップページに表示されます。部分一致・全角半角どちらでもOK。"
)

# ---------------- 検索 ----------------
with st.form("search_form"):
    query_input = st.text_input(
        "地番（番地）を入力", placeholder="例）26-7 / 巨勢町 112-3 / 88",
        value=st.session_state.query,
    )
    submitted = st.form_submit_button("🔍 検索してマップを開く", use_container_width=True, type="primary")

if submitted:
    if not query_input:
        st.warning("地番を入力してください。")
    else:
        pins, _ = extract_features(st.session_state.geojsons)
        ranked = rank_hits(pins, query_input)
        if not ranked:
            st.warning("該当なし。地番の一部や小字名で試してください。")
        else:
            st.session_state.hits = ranked
            st.session_state.query = query_input
            st.session_state.current_index = 0
            st.switch_page(MAP_PAGE)

st.divider()

# ---------------- データ読み込み ----------------
st.subheader("農地データの読み込み")
uploaded = st.file_uploader(
    "GeoJSON（農地ピン / 筆ポリゴン）", type=["geojson", "json"],
    accept_multiple_files=True,
)
c1, c2 = st.columns(2)
if c1.button("サンプル表示", use_container_width=True):
    st.session_state.geojsons = [sample_geojson()]
    st.session_state.data_label = "サンプル：佐賀市周辺のダミー圃場 8件"
    st.session_state.hits = []
    st.session_state.query = ""
if c2.button("クリア", use_container_width=True):
    st.session_state.geojsons = []
    st.session_state.data_label = "データをクリアしました"
    st.session_state.hits = []
    st.session_state.query = ""

if uploaded:
    gjs = []
    for uf in uploaded:
        try:
            gjs.append(json.loads(uf.getvalue().decode("utf-8")))
        except Exception as e:  # noqa
            st.error(f"{uf.name} を読み込めませんでした: {e}")
    if gjs:
        st.session_state.geojsons = gjs
        st.session_state.data_label = f"アップロード：{len(uploaded)}ファイル"
        st.session_state.hits = []
        st.session_state.query = ""

pins_now, _ = extract_features(st.session_state.geojsons)
st.caption(f"📂 {st.session_state.get('data_label', '')}　（全 {len(pins_now)} 件）")

with st.expander("実データの入れ方（eMAFF農地ナビ）"):
    st.markdown(
        "1. [map.maff.go.jp](https://map.maff.go.jp/) を開く\n"
        "2. 佐賀県内の対象エリアまでズーム（14以上）\n"
        "3. 上部「ダウンロード」→ 形式で **GeoJSON** を選択\n"
        "4. 「農地ピン」（地番・面積入り）と必要なら「農地ポリゴン」を取得\n"
        "5. 上のアップローダで読み込む\n\n"
        "※県・市町村単位の一括DLは未対応のため、エリアごとに取得します。"
    )
