"""
佐賀 農地マップ検索 — 3ページ目：本日の巡回ルート
マップページで追加した圃場をまとめて表示し、
近い順への並び替え・複数地点まとめてのGoogle Mapsナビ起動を行う。
"""
import folium
import streamlit as st
from streamlit_folium import st_folium

from lib import MAX_ROUTE_STOPS, multi_stop_google_maps_url, nearest_neighbor_order

SEARCH_PAGE = "views/search.py"
MAP_PAGE = "views/map.py"

st.session_state.setdefault("route_list", [])
route_list = st.session_state.route_list

st.title("📋 本日の巡回ルート")
st.page_link(SEARCH_PAGE, label="⬅ 検索ページへ戻る", icon="🔍")

if not route_list:
    st.info("まだリストに圃場が追加されていません。マップページで「📋 本日のリストに追加」を押すと、ここに表示されます。")
    st.stop()

if len(route_list) > MAX_ROUTE_STOPS:
    st.warning(
        f"Google Mapsの経路案内は一度に{MAX_ROUTE_STOPS}地点までのため、"
        f"ナビ起動には先頭から{MAX_ROUTE_STOPS}件のみ使われます。"
    )

c1, c2, c3 = st.columns([1.4, 1, 1])
with c1:
    st.link_button(
        "🧭 全ルートでGoogle Mapsナビ開始",
        multi_stop_google_maps_url(route_list),
        use_container_width=True, type="primary",
    )
with c2:
    if st.button("🔄 最短ルート順に並び替え", use_container_width=True):
        st.session_state.route_list = nearest_neighbor_order(route_list)
        st.rerun()
with c3:
    if st.button("🗑️ リストを空にする", use_container_width=True):
        st.session_state.route_list = []
        st.rerun()

st.divider()

# ---------------- 巡回順リスト ----------------
for i, p in enumerate(route_list):
    cols = st.columns([0.5, 3, 1, 1])
    cols[0].markdown(f"**{i + 1}**")
    cols[1].markdown(f"**{p['chiban']}**　{p.get('loc', '')}")
    if cols[2].button("地図で見る", key=f"view_{i}", use_container_width=True):
        st.session_state.hits = [p]
        st.session_state.current_index = 0
        st.session_state.query = p["chiban"]
        st.switch_page(MAP_PAGE)
    if cols[3].button("削除", key=f"remove_{i}", use_container_width=True):
        st.session_state.route_list = [x for x in route_list if x is not p]
        st.rerun()

st.divider()

# ---------------- 地図（番号付きマーカー + ルート線） ----------------
center = route_list[0]["latlng"]
fmap = folium.Map(location=center, zoom_start=13, tiles=None)
folium.TileLayer(
    tiles="https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg",
    attr='<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank">地理院タイル</a>(国土地理院)',
    name="航空写真(国土地理院)",
).add_to(fmap)
folium.TileLayer("OpenStreetMap", name="標準地図(OSM)").add_to(fmap)

folium.PolyLine([p["latlng"] for p in route_list], color="#e8471f", weight=3, opacity=0.7).add_to(fmap)

for i, p in enumerate(route_list):
    folium.Marker(
        location=p["latlng"],
        tooltip=f"{i + 1}. {p['chiban']}",
        icon=folium.DivIcon(html=(
            f'<div style="background:#e8471f;color:#fff;border-radius:50%;'
            f'width:26px;height:26px;display:flex;align-items:center;justify-content:center;'
            f'font-weight:bold;font-size:13px;box-shadow:0 0 2px rgba(0,0,0,.5)">{i + 1}</div>'
        )),
    ).add_to(fmap)

bounds = [p["latlng"] for p in route_list]
fmap.fit_bounds(bounds, padding=(30, 30))

folium.LayerControl(position="topright").add_to(fmap)
st_folium(fmap, height=520, use_container_width=True, returned_objects=[])
