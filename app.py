"""
佐賀 農地マップ検索 — 圃場番地から位置を探す
eMAFF農地ナビから取得したGeoJSON(農地ピン / 筆ポリゴン)を読み込み、
所在・地番で部分一致検索して航空写真地図上の該当区画に移動する。
"""
import json
import unicodedata
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="佐賀 農地マップ検索", page_icon="🌾", layout="wide")

SAGA = [33.263, 130.301]  # 佐賀市付近

# ---------------- ユーティリティ ----------------
def normalize(s: str) -> str:
    """全角→半角・ハイフンゆらぎ・空白を吸収して比較用に整える"""
    s = unicodedata.normalize("NFKC", str(s))
    for ch in "ー―－‐─":
        s = s.replace(ch, "-")
    return s.replace(" ", "").replace("\u3000", "").lower()


def pick_chiban(props: dict) -> str:
    keys = list(props.keys())
    for k in keys:
        if any(w in k for w in ("地番", "番地")) or k.lower() in ("chiban", "lot"):
            if props[k] not in (None, ""):
                return str(props[k])
    for k in keys:
        if any(w in k for w in ("所在", "住所", "小字", "大字")) or k.lower() == "address":
            return str(props[k])
    return str(props[keys[0]]) if keys else ""


def pick_location(props: dict) -> str:
    for k in props:
        if any(w in k for w in ("所在", "住所")) or k.lower() == "address":
            return str(props[k])
    return ""


def search_text(props: dict) -> str:
    return normalize(" ".join(str(v) for v in props.values()))


def extract_features(geojsons: list) -> tuple[list, list]:
    """読み込んだGeoJSON群から 農地ピン(点) と 筆ポリゴン を取り出す"""
    pins, polys = [], []
    for gj in geojsons:
        for f in gj.get("features", []):
            geom = f.get("geometry") or {}
            props = f.get("properties") or {}
            gtype = geom.get("type")
            if gtype == "Point":
                lng, lat = geom["coordinates"][:2]
                pins.append({
                    "latlng": [lat, lng],
                    "props": props,
                    "chiban": pick_chiban(props),
                    "loc": pick_location(props),
                    "search": search_text(props),
                })
            elif gtype in ("Polygon", "MultiPolygon"):
                polys.append(f)
    return pins, polys


def popup_html(props: dict) -> str:
    rows = "".join(
        f"<div><span style='color:#888'>{k}：</span>"
        f"<b>{v}</b></div>"
        for k, v in list(props.items())[:12] if v not in (None, "")
    )
    return rows or "属性情報なし"


# ---------------- サンプルデータ ----------------
def sample_geojson() -> dict:
    def pt(lng, lat, chiban, chimoku, area):
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {"所在・地番": chiban, "地目": chimoku,
                           "面積(㎡)": area, "備考": "サンプル"},
        }
    return {
        "type": "FeatureCollection",
        "features": [
            pt(130.298, 33.268, "大字八戸 26-7", "田", "1204"),
            pt(130.305, 33.271, "大字八戸 27-1", "田", "988"),
            pt(130.311, 33.262, "大字巨勢町 112-3", "畑", "756"),
            pt(130.293, 33.259, "大字鍋島 5-14", "田", "1502"),
            pt(130.316, 33.275, "大字兵庫 340-2", "田", "1120"),
            pt(130.289, 33.264, "大字久保泉 88", "畑", "640"),
            pt(130.320, 33.258, "大字木原 201-5", "田", "1340"),
            pt(130.283, 33.272, "大字金立 46-1", "田", "910"),
        ],
    }


# ---------------- 状態 ----------------
if "geojsons" not in st.session_state:
    st.session_state.geojsons = [sample_geojson()]
    st.session_state.data_label = "サンプル：佐賀市周辺のダミー圃場 8件"
if "center" not in st.session_state:
    st.session_state.center = SAGA
    st.session_state.zoom = 12
    st.session_state.hilite = None

# ---------------- サイドバー ----------------
with st.sidebar:
    st.header("🌾 佐賀 農地マップ検索")
    st.caption("所在・地番（番地）で検索すると航空写真上の該当区画に移動します。"
               "部分一致・全角半角どちらでもOK。")

    query = st.text_input("番地・地番・小字で検索", placeholder="例）26-7 / 巨勢町 / 88")

    st.divider()
    st.subheader("農地データの読み込み")
    uploaded = st.file_uploader(
        "GeoJSON（農地ピン / 筆ポリゴン）", type=["geojson", "json"],
        accept_multiple_files=True,
    )
    c1, c2 = st.columns(2)
    if c1.button("サンプル表示", use_container_width=True):
        st.session_state.geojsons = [sample_geojson()]
        st.session_state.data_label = "サンプル：佐賀市周辺のダミー圃場 8件"
        st.session_state.center, st.session_state.zoom = SAGA, 12
        st.session_state.hilite = None
    if c2.button("クリア", use_container_width=True):
        st.session_state.geojsons = []
        st.session_state.data_label = "データをクリアしました"
        st.session_state.hilite = None

    if uploaded:
        gjs = []
        for uf in uploaded:
            try:
                gjs.append(json.loads(uf.getvalue().decode("utf-8")))
            except Exception as e:  # noqa
                st.error(f"{uf.name} を読み込めませんでした: {e}")
        if gjs:
            st.session_state.geojsons = gjs
            st.session_state.hilite = None

    st.caption(f"📂 {st.session_state.get('data_label', '')}")

    with st.expander("実データの入れ方（eMAFF農地ナビ）"):
        st.markdown(
            "1. [map.maff.go.jp](https://map.maff.go.jp/) を開く\n"
            "2. 佐賀県内の対象エリアまでズーム（14以上）\n"
            "3. 上部「ダウンロード」→ 形式で **GeoJSON** を選択\n"
            "4. 「農地ピン」（地番・面積入り）と必要なら「農地ポリゴン」を取得\n"
            "5. 上のアップローダで読み込む\n\n"
            "※県・市町村単位の一括DLは未対応のため、エリアごとに取得します。"
        )

# ---------------- データ展開・検索 ----------------
pins, polys = extract_features(st.session_state.geojsons)

hits = pins
if query:
    q = normalize(query)
    hits = [p for p in pins if q in p["search"]]

# 検索結果一覧
left, right = st.columns([1, 2.4])
with left:
    if query:
        st.write(f"**{len(hits)} 件ヒット**")
    else:
        st.write(f"全 **{len(pins)}** 件")

    if not pins:
        st.info("データ未読み込み。サイドバーの「サンプル表示」またはeMAFFのGeoJSONを読み込んでください。")
    elif query and not hits:
        st.warning("該当なし。地番の一部や小字名で試してください。")

    for i, p in enumerate(hits[:100]):
        label = p["chiban"] or "（地番不明）"
        sub = p["loc"] or ""
        if st.button(f"📍 {label}\n\n{sub}", key=f"hit{i}", use_container_width=True):
            st.session_state.center = p["latlng"]
            st.session_state.zoom = 17
            st.session_state.hilite = p["latlng"]

# ---------------- 地図 ----------------
with right:
    fmap = folium.Map(location=st.session_state.center,
                      zoom_start=st.session_state.zoom, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="航空写真(Esri)", max_zoom=19,
    ).add_to(fmap)
    folium.TileLayer("OpenStreetMap", name="標準地図(OSM)").add_to(fmap)

    for f in polys:
        folium.GeoJson(
            f, style_function=lambda _: {
                "color": "#c9821f", "weight": 1.5,
                "fillColor": "#c9821f", "fillOpacity": 0.12},
        ).add_to(fmap)

    for p in pins:
        folium.CircleMarker(
            location=p["latlng"], radius=6, color="#ffffff", weight=1.5,
            fill=True, fill_color="#3a6b35", fill_opacity=0.95,
            popup=folium.Popup(popup_html(p["props"]), max_width=260),
            tooltip=p["chiban"],
        ).add_to(fmap)

    if st.session_state.hilite:
        folium.CircleMarker(
            location=st.session_state.hilite, radius=13,
            color="#e8471f", weight=3, fill=False,
        ).add_to(fmap)

    folium.LayerControl(position="topright").add_to(fmap)
    st_folium(fmap, height=620, use_container_width=True,
              returned_objects=[])
