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
# 自訂 CSS (含黑條去除與美化)
# -----------------------------
st.markdown("""
<style>
    /* 背景與標題 */
    .stApp {
        background: linear-gradient(135deg, ##FF8888 0%, #e2d1c3 100%);
    }
    h1 {
        color: #d35400 !important;
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
    }

    /* 餐廳卡片 */
    .res-card {
        background: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border-left: 10px solid #FF512F;
        margin-bottom: 1rem;
    }
    .res-card h2 { color: #2c3e50 !important; margin-bottom: 0.5rem; }
    .res-card p { color: #5f6c72 !important; margin: 0.2rem 0; }

    /* 移除 streamlit-geolocation 的黑條並美化按鈕 */
    .streamlit-geolocation {
        background-color: transparent !important;
        padding: 0 !important;
        margin-bottom: 10px;
    }
    .streamlit-geolocation > button {
        background: linear-gradient(45deg, #FF512F, #DD2476) !important;
        color: white !important;
        border: none !important;
        padding: 12px 24px !important;
        border-radius: 50px !important;
        width: 100% !important;
        font-weight: bold !important;
        box-shadow: 0 4px 15px rgba(221, 36, 118, 0.3) !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    .streamlit-geolocation > button::after {
        content: " 點擊取得目前 GPS 位置";
        margin-left: 8px;
    }

    /* 一般按鈕 */
    div.stButton > button {
        background: linear-gradient(45deg, #FF512F, #DD2476) !important;
        color: white !important;
        border-radius: 999px !important;
        font-weight: 700 !important;
        border: none !important;
    }

    /* 標籤樣式 */
    .tag {
        background: #fff5f0;
        color: #e67e22;
        border: 1px solid #ffdecb;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        margin-right: 0.4rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 工具函式 (Haversine, URL 等)
# -----------------------------
def haversine_meters(lat1, lon1, lat2, lon2):
    r = 6371000
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(1 - a))

def format_distance(meters):
    return f"{int(meters)}m" if meters < 1000 else f"{meters/1000:.1f}km"

@st.cache_data(ttl=300, show_spinner=False)
def geocode_address_cached(api_key, address):
    gmaps = googlemaps.Client(key=api_key)
    res = gmaps.geocode(address)
    if not res: return None
    loc = res[0]["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"], "label": res[0].get("formatted_address")}

@st.cache_data(ttl=300, show_spinner=False)
def search_restaurants(api_key, lat, lng, radius, keyword, open_now, min_rating):
    gmaps = googlemaps.Client(key=api_key)
    res = gmaps.places_nearby(location=(lat, lng), radius=radius, type='restaurant', keyword=keyword, open_now=open_now, language='zh-TW')
    
    results = []
    for p in res.get('results', []):
        if p.get('rating', 0) < min_rating: continue
        p_lat, p_lng = p['geometry']['location']['lat'], p['geometry']['location']['lng']
        results.append({
            "名稱": p['name'], "評價": p.get('rating', 0), "評論數": p.get('user_ratings_total', 0),
            "地址": p.get('vicinity', ''), "place_id": p['place_id'],
            "距離": haversine_meters(lat, lng, p_lat, p_lng),
            "地圖連結": f"https://www.google.com/maps/search/?api=1&query={p['name']}&query_place_id={p['place_id']}",
            "嵌入連結": f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{p['place_id']}"
        })
    return sorted(results, key=lambda x: x['距離'])

# -----------------------------
# 初始化 Session State
# -----------------------------
for key in ["res_list", "selected_res", "target_lat", "target_lng", "target_label"]:
    if key not in st.session_state: st.session_state[key] = None

api_key = st.secrets["GMAP_API_KEY"]

# -----------------------------
# 側邊欄設定
# -----------------------------
with st.sidebar:
    st.title("🍔 搜尋條件")
    mode = st.radio("定位方式", ["自訂地址", "目前位置"])
    radius = st.slider("搜尋範圍 (m)", 300, 5000, 1000, 100)
    min_rating = st.slider("最低評分", 0.0, 5.0, 3.5, 0.1)
    cuisine = st.selectbox("想吃什麼", ["不限", "拉麵", "火鍋", "咖啡", "燒肉", "早午餐"])

# -----------------------------
# 定位邏輯修正 (關鍵區塊)
# -----------------------------
if mode == "目前位置":
    st.subheader("📍 點擊按鈕定位")
    loc_data = streamlit_geolocation()
    if loc_data and loc_data.get("latitude"):
        st.session_state.target_lat = loc_data["latitude"]
        st.session_state.target_lng = loc_data["longitude"]
        st.session_state.target_label = "您的目前位置"
        st.success("GPS 定位成功")
else:
    st.subheader("🏠 輸入地址")
    addr_input = st.text_input("請輸入地址或商圈", placeholder="例如：西門町")
    if st.button("📌 確認地址", use_container_width=True):
        geo = geocode_address_cached(api_key, addr_input)
        if geo:
            st.session_state.target_lat = geo["lat"]
            st.session_state.target_lng = geo["lng"]
            st.session_state.target_label = geo["label"]
            st.success(f"已定位到：{geo['label']}")

# -----------------------------
# 主畫面顯示與抽獎
# -----------------------------
st.title("🍜 今天吃什麼？美食轉盤")

if st.session_state.target_lat:
    st.write(f"📍 目前搜尋中心：**{st.session_state.target_label}**")
    
    if st.button("🔍 搜尋附近美食", use_container_width=True):
        with st.spinner("搜尋中..."):
            kw = "" if cuisine == "不限" else cuisine
            results = search_restaurants(api_key, st.session_state.target_lat, st.session_state.target_lng, radius, kw, False, min_rating)
            st.session_state.res_list = results
            if results: st.session_state.selected_res = random.choice(results)

    if st.session_state.res_list:
        if st.button("🎰 再抽一次", use_container_width=True):
            st.session_state.selected_res = random.choice(st.session_state.res_list)
            st.balloons()
        
        if st.session_state.selected_res:
            pick = st.session_state.selected_res
            st.markdown(f"""
            <div class="res-card">
                <h2>{pick['名稱']}</h2>
                <p>⭐ 評分：{pick['評價']} ({pick['評論數']} 則)</p>
                <p>📍 地址：{pick['地址']}</p>
                <p>🚶 距離中心：{format_distance(pick['距離'])}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.link_button("🚀 導航前往", pick["地圖連結"], use_container_width=True)
            with st.expander("🗺️ 查看地圖預覽", expanded=True):
                st.components.v1.iframe(pick["嵌入連結"], height=400)
else:
    st.info("請先完成定位（輸入地址或使用 GPS）。")
