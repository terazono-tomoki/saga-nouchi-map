"""
佐賀 農地マップ検索 — 2ページ目：マップ表示 / ナビ起動
1ページ目で検索した地番の位置を航空写真地図上に表示し、
Google Mapsのターンバイターン案内へワンタップで引き継ぐ。
"""
import folium
import streamlit as st
from streamlit_folium import st_folium

from lib import extract_features, google_maps_url, popup_html

st.set_page_config(page_title="佐賀 農地マップ検索 - マップ", page_icon="🗺️", layout="wide")

SEARCH_PAGE = "app.py"

hits = st.session_state.get("hits", [])
query = st.session_state.get("query", "")

if not hits:
    st.info("先に1ページ目で地番を検索してください。")
    st.page_link(SEARCH_PAGE, label="⬅ 検索ページへ戻る", icon="🔍")
    st.stop()

current_index = st.session_state.get("current_index", 0)
current = hits[current_index]
lat, lng = current["latlng"]

# ---------------- 最上部：ナビ起動 ----------------
st.page_link(SEARCH_PAGE, label="⬅ 検索ページへ戻る", icon="🔍")
nav_col, info_col = st.columns([1, 2])
with nav_col:
    st.link_button(
        "🧭 Google Mapsでナビ開始",
        google_maps_url(lat, lng),
        use_container_width=True,
        type="primary",
    )
with info_col:
    st.markdown(f"**「{query}」** で {len(hits)} 件ヒット　→　現在地図表示中：**{current['chiban']}**")

# 複数ヒット時の切り替え
if len(hits) > 1:
    cols = st.columns(min(len(hits), 6))
    for i, p in enumerate(hits):
        col = cols[i % len(cols)]
        label = p["chiban"] or "（地番不明）"
        if col.button(label, key=f"hit{i}", type="primary" if i == current_index else "secondary",
                      use_container_width=True):
            st.session_state.current_index = i
            st.rerun()

st.divider()

# ---------------- 地図 ----------------
pins, polys = extract_features(st.session_state.get("geojsons", []))

fmap = folium.Map(location=[lat, lng], zoom_start=18, tiles=None)
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

folium.CircleMarker(
    location=[lat, lng], radius=13, color="#e8471f", weight=3, fill=False,
).add_to(fmap)

folium.LayerControl(position="topright").add_to(fmap)
st_folium(fmap, height=620, use_container_width=True, returned_objects=[])
