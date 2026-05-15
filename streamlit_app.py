import streamlit as st
from streamlit_js_eval import get_geolocation
import googlemaps
import random

# --- 設定頁面 ---
st.set_page_config(page_title="今天吃什麼？美食轉盤", page_icon="🍱", layout="centered")

# --- 1. CSS 修正：確保文字顏色為深灰色/黑色 ---
st.markdown("""
    <style>
    .stApp { background-color: #FDFCF0; }
    
    /* 強制設定卡片內文字顏色 */
    .res-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        border-left: 10px solid #FF4B2B;
        margin-bottom: 20px;
    }
    .res-card h2 { color: #222222 !important; margin-bottom: 10px; }
    .res-card p { color: #444444 !important; font-size: 16px; margin: 5px 0; }
    
    /* 按鈕樣式 */
    div.stButton > button {
        border-radius: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 初始化 API ---
api_key = st.secrets["GMAP_API_KEY"]
gmaps = googlemaps.Client(key=api_key)

# --- 側邊欄 ---
with st.sidebar:
    st.title("美食設定")
    mode = st.radio("📍 定位方式", ["目前位置", "自訂地址"])
    radius = st.slider("📏 搜尋範圍 (公尺)", 300, 5000, 1000, 100)
    
    target_lat, target_lng = None, None
    if mode == "目前位置":
        loc = get_geolocation()
        if loc:
            target_lat, target_lng = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        address = st.text_input("🏠 輸入目標區域")
        if address:
            res = gmaps.geocode(address)
            if res:
                target_lat, target_lng = res[0]['geometry']['location']['lat'], res[0]['geometry']['location']['lng']

# --- 主畫面 ---
st.title("🍜 今天吃什麼？")

if target_lat and target_lng:
    # 搜尋按鈕
    if st.button('🔍 搜尋附近美食', use_container_width=True):
        res = gmaps.places_nearby(location=(target_lat, target_lng), radius=radius, type='restaurant', language='zh-TW')
        results = []
        for p in res.get('results', []):
            results.append({
                '名稱': p['name'],
                '評價': p.get('rating', 0),
                '地址': p.get('vicinity', ''),
                '評論數': p.get('user_ratings_total', 0),
                '地圖連結': f"https://www.google.com/maps/search/?api=1&query={p['name']}&query_place_id={p.get('place_id')}",
                '嵌入連結': f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{p.get('place_id')}"
            })
        st.session_state['res_list'] = results
        # 搜尋完後自動抽第一次
        if results:
            st.session_state['selected_res'] = random.choice(results)

    # 抽獎邏輯
    if 'res_list' in st.session_state and st.session_state['res_list']:
        
        # 這裡就是「再抽一次」的功能：直接點擊就會觸發 session_state 更新
        if st.button('🎰 命運轉盤 / 再抽一次', use_container_width=True):
            st.session_state['selected_res'] = random.choice(st.session_state['res_list'])
            st.balloons()

        if 'selected_res' in st.session_state:
            pick = st.session_state['selected_res']
            
            # 顯示卡片
            st.markdown(f"""
                <div class="res-card">
                    <h2>{pick['名稱']}</h2>
                    <p><b>⭐ 評分：</b>{pick['評價']} ({pick['評論數']} 則評論)</p>
                    <p><b>📍 地址：</b>{pick['地址']}</p>
                </div>
            """, unsafe_allow_html=True)

            # 導航按鈕
            st.link_button("🚀 導航前往", pick['地圖連結'], use_container_width=True)

            # 地圖區
            with st.expander("🗺️ 查看地圖預覽", expanded=True):
                st.components.v1.iframe(pick['嵌入連結'], height=400)
else:
    st.info("請在左側選擇定位方式來開始。")
