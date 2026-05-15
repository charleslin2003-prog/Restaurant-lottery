import streamlit as st
import googlemaps
import random
import time
import html
from math import radians, sin, cos, sqrt, atan2
from streamlit_js_eval import get_geolocation

# -----------------------------
# 基本設定
# -----------------------------
st.set_page_config(
    page_title="今天吃什麼？美食轉盤",
    page_icon="🍱",
    layout="centered"
)

# -----------------------------
# 自訂 CSS
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #F5DEB3 0%, #e2d1c3 100%);
    }

    h1 {
        color: #d35400 !important;
        font-family: 'Helvetica Neue', sans-serif;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
    }

    .res-card {
        background: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: none;
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }

    .res-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(211, 84, 0, 0.15);
        border: 1px solid #FF512F;
    }

    .res-card h2 {
        color: #2c3e50 !important;
        font-size: 1.5rem !important;
        margin-bottom: 0.5rem;
    }

    .res-card p {
        color: #5f6c72 !important;
        margin-bottom: 0.35rem;
    }

    div.stButton > button {
        background: linear-gradient(45deg, #FF512F, #DD2476) !important;
        color: white !important;
        border: none !important;
        padding: 0.7rem 1.2rem !important;
        border-radius: 999px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 15px rgba(221, 36, 118, 0.25) !important;
    }

    div.stLinkButton > a {
        background-color: #34495e !important;
        color: white !important;
        border-radius: 999px !important;
        text-decoration: none !important;
        display: inline-block;
        text-align: center;
        padding: 0.7rem 1rem !important;
        border: none !important;
    }

    .small-note {
        color: #6b7280;
        font-size: 0.92rem;
    }

    .tag {
        background: #fff5f0;
        color: #e67e22;
        border: 1px solid #ffdecb;
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session State 初始化
# -----------------------------
defaults = {
    "res_list": [],
    "selected_res": None,
    "draw_history": [],
    "target_lat": None,
    "target_lng": None,
    "target_label": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -----------------------------
# 工具函式
# -----------------------------
def safe_text(x):
    return html.escape(str(x or ""))

def haversine_meters(lat1, lon1, lat2, lon2):
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c

def format_distance(meters):
    if meters is None:
        return "未知"
    if meters < 1000:
        return f"{int(meters)} 公尺"
    return f"{meters / 1000:.1f} 公里"

def build_maps_url(name, place_id):
    return f"https://www.google.com/maps/search/?api=1&query={name}&query_place_id={place_id}"

def build_embed_url(api_key, place_id):
    return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{place_id}"

def place_open_status(p):
    if "opening_hours" in p and isinstance(p["opening_hours"], dict):
        if "open_now" in p["opening_hours"]:
            return "營業中" if p["opening_hours"]["open_now"] else "目前休息"
    return "未知"

def dollar_text(level):
    if level is None:
        return "未提供"
    try:
        return "💰" * int(level)
    except:
        return "未提供"

@st.cache_data(ttl=300, show_spinner=False)
def geocode_address_cached(api_key, address):
    gmaps = googlemaps.Client(key=api_key)
    res = gmaps.geocode(address)
    if not res:
        return None
    loc = res[0]["geometry"]["location"]
    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "formatted_address": res[0].get("formatted_address", address)
    }

@st.cache_data(ttl=300, show_spinner=False)
def search_nearby_restaurants_cached(
    api_key, lat, lng, radius, open_now_only, min_rating, min_reviews, keyword_text, max_pages
):
    gmaps = googlemaps.Client(key=api_key)
    params = {"location": (lat, lng), "radius": radius, "type": "restaurant", "language": "zh-TW"}
    if open_now_only: params["open_now"] = True
    if keyword_text.strip(): params["keyword"] = keyword_text.strip()

    all_results = []
    seen_place_ids = set()
    res = gmaps.places_nearby(**params)
    pages_fetched = 1

    for p in res.get("results", []):
        pid = p.get("place_id")
        if pid and pid not in seen_place_ids:
            seen_place_ids.add(pid)
            all_results.append(p)

    while res.get("next_page_token") and pages_fetched < max_pages:
        time.sleep(2)
        next_params = {"page_token": res["next_page_token"], "language": "zh-TW"}
        res = gmaps.places_nearby(**next_params)
        pages_fetched += 1
        for p in res.get("results", []):
            pid = p.get("place_id")
            if pid and pid not in seen_place_ids:
                seen_place_ids.add(pid)
                all_results.append(p)

    normalized = []
    for p in all_results:
        rating = p.get("rating", 0) or 0
        reviews = p.get("user_ratings_total", 0) or 0
        if rating < min_rating or reviews < min_reviews: continue

        place_lat = p.get("geometry", {}).get("location", {}).get("lat")
        place_lng = p.get("geometry", {}).get("location", {}).get("lng")
        dist = haversine_meters(lat, lng, place_lat, place_lng) if place_lat and place_lng else None

        normalized.append({
            "名稱": p.get("name", "未命名"),
            "評價": rating,
            "地址": p.get("vicinity", p.get("formatted_address", "")),
            "評論數": reviews,
            "價格等級": p.get("price_level"),
            "營業狀態": place_open_status(p),
            "place_id": p.get("place_id"),
            "緯度": place_lat,
            "經度": place_lng,
            "距離": dist,
            "類型": p.get("types", []),
            "地圖連結": build_maps_url(p.get("name", ""), p.get("place_id", "")),
            "嵌入連結": build_embed_url(api_key, p.get("place_id", "")),
        })

    normalized.sort(key=lambda x: (-(x["評價"] or 0), -(x["評論數"] or 0), x["距離"] if x["距離"] is not None else 10**9))
    return normalized

def weighted_pick(results, excluded_place_ids=None):
    if excluded_place_ids is None: excluded_place_ids = set()
    pool = [r for r in results if r.get("place_id") not in excluded_place_ids]
    if not pool: return None

    weights = []
    for r in pool:
        rating = r.get("評價", 0) or 0
        reviews = r.get("評論數", 0) or 0
        distance = r.get("距離", 99999) or 99999
        open_bonus = 1.15 if r.get("營業狀態") == "營業中" else 1.0

        if distance <= 300: distance_factor = 1.35
        elif distance <= 800: distance_factor = 1.18
        elif distance <= 1500: distance_factor = 1.05
        else: distance_factor = 0.9

        review_factor = min(reviews, 500) / 120
        base = max(1.0, rating * 2.2 + review_factor)
        weights.append(base * distance_factor * open_bonus)

    return random.choices(pool, weights=weights, k=1)[0]

def render_card(place):
    tags_html = "".join([f"<span class='tag'>{safe_text(t)}</span>" for t in place.get("類型", [])[:5]])
    st.markdown(f"""
    <div class="res-card">
        <h2>{safe_text(place["名稱"])}</h2>
        <p><b>⭐ 評分：</b>{place["評價"]}（{place["評論數"]} 則評論）</p>
        <p><b>📍 地址：</b>{safe_text(place["地址"])}</p>
        <p><b>🚶 距離：</b>{safe_text(format_distance(place["距離"]))}</p>
        <p><b>🕒 狀態：</b>{safe_text(place["營業狀態"])}</p>
        <p><b>💵 價格：</b>{dollar_text(place["價格等級"])}</p>
        <div style="margin-top: 0.7rem;">{tags_html}</div>
    </div>
    """, unsafe_allow_html=True)

def reset_draw_state():
    st.session_state["selected_res"] = None
    st.session_state["draw_history"] = []

# -----------------------------
# API 金鑰與側邊欄設定
# -----------------------------
try:
    api_key = st.secrets["GMAP_API_KEY"]
except Exception:
    st.error("找不到 API Key")
    st.stop()

with st.sidebar:
    st.title("美食設定")
    radius = st.slider("📏 搜尋範圍（公尺）", 300, 5000, 1200, 100)
    max_pages = st.selectbox("📄 搜尋頁數", [1, 2, 3], index=1)
    open_now_only = st.checkbox("🟢 只看目前營業中", value=False)
    
    st.markdown("---")
    min_rating = st.slider("⭐ 最低評分", 0.0, 5.0, 3.5, 0.1)
    min_reviews = st.slider("🗣️ 最低評論數", 0, 500, 20, 10)
    cuisine = st.selectbox("🍜 想吃什麼", ["不限", "拉麵", "火鍋", "便當", "咖啡", "素食", "牛肉麵", "早午餐", "壽司", "韓式", "義式", "燒肉"])
    keyword_text = "" if cuisine == "不限" else cuisine

    st.markdown("---")
    avoid_repeat = st.checkbox("🎯 盡量不重複抽中", value=True)
    weighted_mode = st.checkbox("⚖️ 加權抽籤", value=True)

# -----------------------------
# 主畫面與定位區
# -----------------------------
st.title("🍜 今天吃什麼？美食轉盤")
st.caption("搜尋附近餐廳，交給命運決定今天吃哪一家。")

# 將定位切換移到主畫面
mode = st.radio("📍 選擇定位方式：", ["目前位置", "自訂地址"], horizontal=True)

target_lat, target_lng, target_label = None, None, ""

if mode == "目前位置":
    loc = get_geolocation() # 隱形抓取定位，不會有醜醜的黑色按鈕
    if loc:
        target_lat = loc['coords']['latitude']
        target_lng = loc['coords']['longitude']
        target_label = "目前位置"
        st.session_state["target_lat"], st.session_state["target_lng"], st.session_state["target_label"] = target_lat, target_lng, target_label
        st.success(f"已取得定位：{target_lat:.6f}, {target_lng:.6f}")
    else:
        st.info("🔄 正在等待瀏覽器定位權限... (若無反應請檢查網址列的定位權限)")

else:
    address = st.text_input("🏠 輸入目標地址或商圈", placeholder="例如：台北車站、信義區")
    if st.button("📌 解析地址", use_container_width=True):
        if address.strip():
            geo = geocode_address_cached(api_key, address.strip())
            if geo:
                st.session_state["target_lat"], st.session_state["target_lng"], st.session_state["target_label"] = geo["lat"], geo["lng"], geo["formatted_address"]
                reset_draw_state()
                st.success(f"地址解析成功：{geo['formatted_address']}")
            else:
                st.error("找不到這個地址，請換個關鍵字。")

# -----------------------------
# 搜尋與結果顯示區
# -----------------------------
if st.session_state["target_lat"] and st.session_state["target_lng"]:
    st.markdown("---")
    st.write(f"目前搜尋中心：**{st.session_state['target_label'] or '已選定位置'}**")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔍 搜尋附近美食", use_container_width=True):
            reset_draw_state()
            with st.spinner('正在尋找附近美食...'):
                results = search_nearby_restaurants_cached(
                    api_key=api_key, lat=st.session_state["target_lat"], lng=st.session_state["target_lng"],
                    radius=radius, open_now_only=open_now_only, min_rating=min_rating, min_reviews=min_reviews,
                    keyword_text=keyword_text, max_pages=max_pages
                )
            st.session_state["res_list"] = results
            if results:
                first_pick = weighted_pick(results) if weighted_mode else random.choice(results)
                st.session_state["selected_res"] = first_pick
                st.session_state["draw_history"] = [first_pick["place_id"]]
                st.success(f"找到 {len(results)} 家符合條件的餐廳。")
            else:
                st.warning("沒有找到餐廳，請放寬篩選條件。")

    with col2:
        if st.button("🗑️ 清除", use_container_width=True):
            st.session_state["res_list"] = []
            reset_draw_state()

    if st.session_state["res_list"]:
        st.markdown(f"### 🍽️ 候選餐廳：{len(st.session_state['res_list'])} 家")
        colA, colB = st.columns(2)

        with colA:
            if st.button("🎰 命運轉盤 / 再抽一次", use_container_width=True):
                excluded = set(st.session_state["draw_history"]) if avoid_repeat else set()
                pick = weighted_pick(st.session_state["res_list"], excluded) if weighted_mode else random.choice([r for r in st.session_state["res_list"] if r["place_id"] not in excluded] or [None])
                
                if not pick:
                    st.session_state["draw_history"] = []
                    pick = weighted_pick(st.session_state["res_list"]) if weighted_mode else random.choice(st.session_state["res_list"])
                
                st.session_state["selected_res"] = pick
                if pick["place_id"] not in st.session_state["draw_history"]:
                    st.session_state["draw_history"].append(pick["place_id"])
                st.balloons()

        with colB:
            if st.button("🔄 重新洗牌", use_container_width=True):
                st.session_state["draw_history"] = []

        if st.session_state["selected_res"]:
            pick = st.session_state["selected_res"]
            st.markdown("### 🏆 今天吃這家")
            render_card(pick)
            st.link_button("🚀 導航前往", pick["地圖連結"], use_container_width=True)
            with st.expander("🗺️ 查看地圖預覽", expanded=True):
                st.components.v1.iframe(pick["嵌入連結"], height=420)
else:
    st.info("請在上方選擇定位方式，取得位置後即可開始。")
