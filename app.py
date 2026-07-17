"""
佐賀 農地マップ検索 — エントリーポイント
1ページ目（検索）と2ページ目（マップ）を st.navigation で束ねる。
ページのファイル名はASCIIのみとし、表示名は title= で日本語を指定する
（絵文字・非ASCII文字を含むファイル名は、Streamlit Cloud 環境でのデプロイ時に
switch_page が正しく解決できず StreamlitAPIException になることがあるため）。
"""
import streamlit as st

st.set_page_config(page_title="佐賀 農地マップ検索", page_icon="🌾", layout="wide")

search_page = st.Page("views/search.py", title="検索", icon="🔍", default=True)
map_page = st.Page("views/map.py", title="マップ", icon="🗺️")

pg = st.navigation([search_page, map_page])
pg.run()
