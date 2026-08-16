"""
佐賀 農地マップ検索 — 共通ロジック
検索ページ（app.py）とマップページ（pages/1_マップ.py）から共有する。
"""
import math
import unicodedata

MAX_ROUTE_STOPS = 10  # Google Maps方向案内URLの現実的な上限（出発地+経由地+目的地）

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


def _ring_centroid(ring: list) -> tuple:
    """閉じたリング（[[lng,lat], ...]）の面積重心を返す（shoelace公式）"""
    n = len(ring)
    area2 = cx = cy = 0.0
    for i in range(n - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area2) < 1e-12:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return cx / (3 * area2), cy / (3 * area2)


def _ring_area(ring: list) -> float:
    area2 = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        area2 += x0 * y1 - x1 * y0
    return abs(area2) / 2


def polygon_centroid_latlng(geom: dict) -> list:
    """Polygon/MultiPolygonの重心を [lat, lng] で返す"""
    coords = geom.get("coordinates") or []
    gtype = geom.get("type")
    if gtype == "Polygon":
        rings = [coords[0]] if coords else []
    else:  # MultiPolygon: 面積が一番大きい部分を代表点にする
        exterior_rings = [poly[0] for poly in coords if poly]
        rings = [max(exterior_rings, key=_ring_area)] if exterior_rings else []
    if not rings or len(rings[0]) < 3:
        return [0.0, 0.0]
    lng, lat = _ring_centroid(rings[0])
    return [lat, lng]


def extract_features(geojsons: list) -> tuple[list, list]:
    """読み込んだGeoJSON群から 検索対象のピン(点+筆ポリゴン重心) と 筆ポリゴン(描画用) を取り出す"""
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
                pins.append({
                    "latlng": polygon_centroid_latlng(geom),
                    "props": props,
                    "chiban": pick_chiban(props),
                    "loc": pick_location(props),
                    "search": search_text(props),
                })
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


def haversine_km(a: list, b: list) -> float:
    """2地点間の直線距離(km)。道路距離ではなく巡回順の目安計算用の簡易近似"""
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def nearest_neighbor_order(stops: list) -> list:
    """最初の1件を起点に、直線距離が近い順へ並べ替える（簡易巡回順・最適解ではない）"""
    if len(stops) <= 2:
        return list(stops)
    remaining = list(stops[1:])
    ordered = [stops[0]]
    while remaining:
        last = ordered[-1]
        nxt = min(remaining, key=lambda p: haversine_km(last["latlng"], p["latlng"]))
        ordered.append(nxt)
        remaining.remove(nxt)
    return ordered


def multi_stop_google_maps_url(stops: list) -> str:
    """複数地点を順番にめぐるGoogle Mapsの経路案内URL（先頭が出発地）"""
    points = [f"{p['latlng'][0]},{p['latlng'][1]}" for p in stops[:MAX_ROUTE_STOPS]]
    origin, destination = points[0], points[-1]
    waypoints = points[1:-1]
    url = (f"https://www.google.com/maps/dir/?api=1&origin={origin}"
           f"&destination={destination}&travelmode=driving")
    if waypoints:
        url += "&waypoints=" + "|".join(waypoints)
    return url


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
