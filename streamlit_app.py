import streamlit as st
import googlemaps
import random
import time
import html
from math import radians, sin, cos, sqrt, atan2
from streamlit_geolocation import streamlit_geolocation

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
        background: linear-gradient(135deg, #fdfcfb 0%, #000000 100%);
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
    box-shadow: 0 15px 35px rgba(211, 84, 0, 0.15); /* 加入主題色的淡淡陰影 */
    border: 1px solid #FF512F; /* 滑鼠移入時顯現細邊框 */
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

    /* 美化 streamlit-geolocation 的按鈕 */
    .streamlit-geolocation > button {
        background-color: #f0f2f6 !important; /* 淺灰色背景 */
        color: #31333f !important; /* 深灰色文字 */
        border-radius: 999px !important; /* 圓角 */
        padding: 0.5rem 1rem !important; /* 內邊距 */
        border: 1px solid #d1d5db !important; /* 細邊框 */
        font-weight: 500 !important; /* 中等粗細字體 */
        transition: background-color 0.3s ease !important; /* 漸變效果 */
        display: flex !important; /* 水平排列 */
        align-items: center !important; /* 垂直居中 */
        gap: 0.5rem !important; /* 圖示和文字間距 */
    }

    .streamlit-geolocation > button:hover {
        background-color: #e5e7eb !important; /* 滑鼠懸停時的顏色 */
    }

    .streamlit-geolocation > button:active {
        background-color: #d1d5db !important; /* 按下時的顏色 */
    }
    
    /* 調整圖示大小和顏色 */
    .streamlit-geolocation > button svg {
        width: 1rem !important;
        height: 1rem !important;
        fill: #31333f !important; /* 圖示顏色 */
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
        background: #fff5f0; /* 極淡的橘色 */
        color: #e67e22; /* 餐廳類型用主題色 */
        border: 1px solid #ffdecb;
        display: inline-block;
        background: #f4f4f5;
        color: #374151;
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

@st.cache_data(ttl=300, show_spinner=True)
def search_nearby_restaurants_cached(
    api_key,
    lat,
    lng,
    radius,
    open_now_only,
    min_rating,
    min_reviews,
    keyword_text,
    max_pages
):
    gmaps = googlemaps.Client(key=api_key)

    params = {
        "location": (lat, lng),
        "radius": radius,
        "type": "restaurant",
        "language": "zh-TW",
    }

    if open_now_only:
        params["open_now"] = True

    if keyword_text.strip():
        params["keyword"] = keyword_text.strip()

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
        next_params = {
            "page_token": res["next_page_token"],
            "language": "zh-TW",
        }
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

        if rating < min_rating:
            continue
        if reviews < min_reviews:
            continue

        place_lat = p.get("geometry", {}).get("location", {}).get("lat")
        place_lng = p.get("geometry", {}).get("location", {}).get("lng")

        dist = None
        if place_lat is not None and place_lng is not None:
            dist = haversine_meters(lat, lng, place_lat, place_lng)

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

    normalized.sort(key=lambda x: (
        -(x["評價"] or 0),
        -(x["評論數"] or 0),
        x["距離"] if x["距離"] is not None else 10**9
    ))

    return normalized

def weighted_pick(results, excluded_place_ids=None):
    if excluded_place_ids is None:
        excluded_place_ids = set()

    pool = [r for r in results if r.get("place_id") not in excluded_place_ids]
    if not pool:
        return None

    weights = []
    for r in pool:
        rating = r.get("評價", 0) or 0
        reviews = r.get("評論數", 0) or 0
        distance = r.get("距離", 99999) or 99999
        open_bonus = 1.15 if r.get("營業狀態") == "營業中" else 1.0

        distance_factor = 1.0
        if distance <= 300:
            distance_factor = 1.35
        elif distance <= 800:
            distance_factor = 1.18
        elif distance <= 1500:
            distance_factor = 1.05
        else:
            distance_factor = 0.9

        review_factor = min(reviews, 500) / 120
        base = max(1.0, rating * 2.2 + review_factor)
        weight = base * distance_factor * open_bonus
        weights.append(weight)

    return random.choices(pool, weights=weights, k=1)[0]

def render_card(place):
    name = safe_text(place["名稱"])
    address = safe_text(place["地址"])
    rating = place["評價"]
    reviews = place["評論數"]
    price = dollar_text(place["價格等級"])
    status = safe_text(place["營業狀態"])
    distance = safe_text(format_distance(place["距離"]))

    types = place.get("類型", [])
    type_tags = []
    for t in types[:5]:
        type_tags.append(f"<span class='tag'>{safe_text(t)}</span>")
    tags_html = "".join(type_tags)

    st.markdown(f"""
    <div class="res-card">
        <h2>{name}</h2>
        <p><b>⭐ 評分：</b>{rating}（{reviews} 則評論）</p>
        <p><b>📍 地址：</b>{address}</p>
        <p><b>🚶 距離：</b>{distance}</p>
        <p><b>🕒 狀態：</b>{status}</p>
        <p><b>💵 價格：</b>{price}</p>
        <div style="margin-top: 0.7rem;">{tags_html}</div>
    </div>
    """, unsafe_allow_html=True)

def reset_draw_state():
    st.session_state["selected_res"] = None
    st.session_state["draw_history"] = []

# -----------------------------
# API 金鑰
# -----------------------------
try:
    api_key = st.secrets["GMAP_API_KEY"]
except Exception:
    st.stop()

# -----------------------------
# 側邊欄
# -----------------------------
with st.sidebar:
    st.title("美食設定")

    mode = st.radio("📍 定位方式", ["目前位置", "自訂地址"])

    radius = st.slider("📏 搜尋範圍（公尺）", 300, 5000, 1200, 100)
    max_pages = st.selectbox("📄 搜尋頁數", [1, 2, 3], index=1)
    open_now_only = st.checkbox("🟢 只看目前營業中", value=False)

    st.markdown("---")
    st.subheader("篩選條件")
    min_rating = st.slider("⭐ 最低評分", 0.0, 5.0, 3.5, 0.1)
    min_reviews = st.slider("🗣️ 最低評論數", 0, 500, 20, 10)

    cuisine = st.selectbox(
        "🍜 想吃什麼",
        ["不限", "拉麵", "火鍋", "便當", "咖啡", "素食", "牛肉麵", "早午餐", "壽司", "韓式", "義式", "燒肉"]
    )
    keyword_text = "" if cuisine == "不限" else cuisine

    st.markdown("---")
    st.subheader("抽籤方式")
    avoid_repeat = st.checkbox("🎯 盡量不重複抽中", value=True)
    weighted_mode = st.checkbox("⚖️ 使用加權抽籤（高評分 / 近距離較容易中）", value=True)

    st.markdown("<div class='small-note'>建議先用 1000~1500 公尺，結果通常比較剛好。</div>", unsafe_allow_html=True)

# -----------------------------
# 定位區
# -----------------------------
target_lat, target_lng, target_label = None, None, ""

if mode == "目前位置":
    st.markdown("### 📍 取得目前位置")
    location = streamlit_geolocation()

    if location and location.get("latitude") is not None and location.get("longitude") is not None:
        target_lat = location["latitude"]
        target_lng = location["longitude"]
        accuracy = location.get("accuracy")
        target_label = "目前位置"

        st.success(f"已取得定位：{target_lat:.6f}, {target_lng:.6f}")
        if accuracy is not None:
            st.caption(f"定位精度：約 {accuracy:.1f} 公尺")
    else:
        st.info("請允許瀏覽器定位權限，成功後會自動帶入目前位置。")

else:
    st.markdown("### 🏠 輸入地址")
    address = st.text_input("請輸入目標地址或商圈", placeholder="例如：台北車站、信義區、台中一中街")

    if st.button("📌 解析地址", use_container_width=True):
        if not address.strip():
            st.warning("請先輸入地址。")
        else:
            geo = geocode_address_cached(api_key, address.strip())
            if geo:
                target_lat = geo["lat"]
                target_lng = geo["lng"]
                target_label = geo["formatted_address"]

                st.session_state["target_lat"] = target_lat
                st.session_state["target_lng"] = target_lng
                st.session_state["target_label"] = target_label

                reset_draw_state()
                st.success(f"地址解析成功：{target_label}")
            else:
                st.error("找不到這個地址，請換個關鍵字再試一次。")

    if st.session_state["target_lat"] and st.session_state["target_lng"]:
        target_lat = st.session_state["target_lat"]
        target_lng = st.session_state["target_lng"]
        target_label = st.session_state["target_label"]
        st.caption(f"目前使用位置：{target_label}")

# 若目前位置模式下成功定位，更新 session_state
if target_lat and target_lng:
    st.session_state["target_lat"] = target_lat
    st.session_state["target_lng"] = target_lng
    st.session_state["target_label"] = target_label

# -----------------------------
# 主畫面
# -----------------------------
st.title("🍜 今天吃什麼？美食轉盤")
st.caption("搜尋附近餐廳，交給命運決定今天吃哪一家。")

if st.session_state["target_lat"] and st.session_state["target_lng"]:
    st.write(
        f"目前搜尋中心：**{st.session_state['target_label'] or '已選定位置'}** "
        f"（{st.session_state['target_lat']:.6f}, {st.session_state['target_lng']:.6f}）"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("🔍 搜尋附近美食", use_container_width=True):
            reset_draw_state()

            # 使用自定義的 spinner
            with st.spinner('正在尋找附近美食...'):
                results = search_nearby_restaurants_cached(
                api_key=api_key,
                lat=st.session_state["target_lat"],
                lng=st.session_state["target_lng"],
                radius=radius,
                open_now_only=open_now_only,
                min_rating=min_rating,
                min_reviews=min_reviews,
                keyword_text=keyword_text,
                max_pages=max_pages
            )

            st.session_state["res_list"] = results

            if results:
                first_pick = weighted_pick(results) if weighted_mode else random.choice(results)
                st.session_state["selected_res"] = first_pick
                st.session_state["draw_history"] = [first_pick["place_id"]]
                st.success(f"找到 {len(results)} 家符合條件的餐廳。")
            else:
                st.warning("沒有找到符合條件的餐廳，請放寬篩選條件或擴大搜尋範圍。")

    with col2:
        if st.button("🗑️ 清除結果", use_container_width=True):
            st.session_state["res_list"] = []
            reset_draw_state()
            st.success("已清除。")

    # 結果區
    if st.session_state["res_list"]:
        st.markdown(f"### 🍽️ 候選餐廳：{len(st.session_state['res_list'])} 家")

        colA, colB = st.columns(2)

        with colA:
            if st.button("🎰 命運轉盤 / 再抽一次", use_container_width=True):
                excluded = set(st.session_state["draw_history"]) if avoid_repeat else set()

                if weighted_mode:
                    pick = weighted_pick(st.session_state["res_list"], excluded_place_ids=excluded)
                else:
                    pool = [r for r in st.session_state["res_list"] if r["place_id"] not in excluded]
                    pick = random.choice(pool) if pool else None

                if pick is None:
                    st.warning("已經抽完所有不重複餐廳，將重置抽籤紀錄。")
                    st.session_state["draw_history"] = []

                    if weighted_mode:
                        pick = weighted_pick(st.session_state["res_list"])
                    else:
                        pick = random.choice(st.session_state["res_list"])

                st.session_state["selected_res"] = pick
                if pick["place_id"] not in st.session_state["draw_history"]:
                    st.session_state["draw_history"].append(pick["place_id"])
                st.balloons()

        with colB:
            if st.button("🔄 重新洗牌", use_container_width=True):
                st.session_state["draw_history"] = []
                st.success("已重置抽籤紀錄。")

        if st.session_state["selected_res"]:
            pick = st.session_state["selected_res"]
            st.markdown("### 🏆 今天吃這家")
            render_card(pick)

            st.link_button("🚀 導航前往", pick["地圖連結"], use_container_width=True)

            with st.expander("🗺️ 查看地圖預覽", expanded=True):
                st.components.v1.iframe(pick["嵌入連結"], height=420)

            with st.expander("📋 看全部候選名單", expanded=False):
                for i, r in enumerate(st.session_state["res_list"], start=1):
                    st.write(
                        f"{i}. {r['名稱']}｜⭐ {r['評價']}｜🗣️ {r['評論數']}｜"
                        f"🚶 {format_distance(r['距離'])}｜🕒 {r['營業狀態']}"
                    )

else:
    st.info("請先在上方或側邊欄選擇定位方式，取得搜尋位置後再開始。")
