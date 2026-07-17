"""
佐賀 農地マップ検索 — 共通ロジック
検索ページ（app.py）とマップページ（pages/1_マップ.py）から共有する。
"""
import unicodedata

SAGA = [33.263, 130.301]  # 佐賀市付近


def normalize(s: str) -> str:
    """全角→半角・ハイフンゆらぎ・空白を吸収して比較用に整える"""
    s = unicodedata.normalize("NFKC", str(s))
    for ch in "ー―－‐─":
        s = s.replace(ch, "-")
    return s.replace(" ", "").replace("　", "").lower()


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


def rank_hits(pins: list, query: str) -> list:
    """地番の完全一致を先頭に、部分一致を後ろに並べて返す"""
    q = normalize(query)
    exact, partial = [], []
    for p in pins:
        if q not in p["search"]:
            continue
        if normalize(p["chiban"]) == q:
            exact.append(p)
        else:
            partial.append(p)
    return exact + partial


def popup_html(props: dict) -> str:
    rows = "".join(
        f"<div><span style='color:#888'>{k}：</span>"
        f"<b>{v}</b></div>"
        for k, v in list(props.items())[:12] if v not in (None, "")
    )
    return rows or "属性情報なし"


def google_maps_url(lat: float, lng: float) -> str:
    """カーナビのターンバイターン案内をそのまま開けるGoogle MapsのURL"""
    return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"


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
