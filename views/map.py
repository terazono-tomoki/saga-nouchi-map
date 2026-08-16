"""
佐賀 農地マップ検索 — 2ページ目：マップ表示 / ナビ起動
1ページ目で検索した地番の位置を航空写真地図上に表示し、
Google Mapsのターンバイターン案内へワンタップで引き継ぐ。
また、巡回リストへの追加・散布記録・圃場メモもここで行う。
"""
import datetime

import folium
import streamlit as st
from streamlit_folium import st_folium

from lib import extract_features, google_maps_url, popup_html

SEARCH_PAGE = "views/search.py"
ROUTE_PAGE = "views/route.py"

st.session_state.setdefault("route_list", [])
st.session_state.setdefault("spray_records", [])
st.session_state.setdefault("field_notes", {})

hits = st.session_state.get("hits", [])
query = st.session_state.get("query", "")

if not hits:
    st.info("先に1ページ目で地番を検索してください。")
    st.page_link(SEARCH_PAGE, label="⬅ 検索ページへ戻る", icon="🔍")
    st.stop()

current_index = st.session_state.get("current_index", 0)
current = hits[current_index]
lat, lng = current["latlng"]
chiban = current["chiban"]

# ---------------- 最上部：ナビ起動 ----------------
st.page_link(SEARCH_PAGE, label="⬅ 検索ページへ戻る", icon="🔍")
nav_col, route_col, info_col = st.columns([1.2, 1.2, 2])
with nav_col:
    st.link_button(
        "🧭 Google Mapsでナビ開始",
        google_maps_url(lat, lng),
        use_container_width=True,
        type="primary",
    )
with route_col:
    already_in_route = any(p["chiban"] == chiban for p in st.session_state.route_list)
    if already_in_route:
        st.button("📋 リスト追加済み", use_container_width=True, disabled=True)
    else:
        if st.button("📋 本日のリストに追加", use_container_width=True):
            st.session_state.route_list.append(current)
            st.rerun()
with info_col:
    st.markdown(f"**「{query}」** で {len(hits)} 件ヒット　→　現在地図表示中：**{chiban}**")
    if st.session_state.route_list:
        st.page_link(ROUTE_PAGE, label=f"📋 本日のリスト（{len(st.session_state.route_list)}件）を見る", icon="📋")

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

# ---------------- 散布記録 / 圃場メモ ----------------
record_col, note_col = st.columns(2)

with record_col:
    with st.expander("📝 散布記録を追加"):
        with st.form(f"record_form_{chiban}"):
            r_date = st.date_input("散布日", value=datetime.date.today())
            r_product = st.text_input("使用農薬・資材")
            r_weather = st.text_input("天候・風速メモ", placeholder="例）晴れ・風速1m")
            if st.form_submit_button("保存", type="primary"):
                st.session_state.spray_records.append({
                    "chiban": chiban, "date": str(r_date),
                    "product": r_product, "weather": r_weather,
                })
                st.success("記録しました。")

        past = [r for r in st.session_state.spray_records if r["chiban"] == chiban]
        if past:
            st.caption(f"この圃場の記録（{len(past)}件）")
            for r in sorted(past, key=lambda r: r["date"], reverse=True):
                st.markdown(f"- {r['date']}｜{r['product'] or '（農薬未記入）'}｜{r['weather']}")

with note_col:
    with st.expander("🗒️ 圃場メモ", expanded=bool(st.session_state.field_notes.get(chiban))):
        note_text = st.text_area(
            "この圃場のメモ（鍵の場所・注意点など）",
            value=st.session_state.field_notes.get(chiban, ""),
            key=f"note_input_{chiban}",
        )
        if st.button("メモを保存", key=f"note_save_{chiban}"):
            st.session_state.field_notes[chiban] = note_text
            st.success("メモを保存しました。")

st.divider()

# ---------------- 地図 ----------------
pins, polys = extract_features(st.session_state.get("geojsons", []))

MAX_ZOOM = 22  # タイルの実解像度(19前後)を超えた分は自動で拡大表示される

fmap = folium.Map(location=[lat, lng], zoom_start=18, max_zoom=MAX_ZOOM, tiles=None)
folium.TileLayer(
    tiles="https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg",
    attr='<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank">地理院タイル</a>(国土地理院)',
    name="航空写真(国土地理院)",
    max_zoom=MAX_ZOOM, max_native_zoom=18,
).add_to(fmap)
folium.TileLayer(
    "OpenStreetMap", name="標準地図(OSM)",
    max_zoom=MAX_ZOOM, max_native_zoom=19,
).add_to(fmap)

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
