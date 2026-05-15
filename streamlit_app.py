import streamlit as st
from streamlit_js_eval import get_geolocation
import googlemaps
import random

# --- 設定頁面外觀 ---
st.set_page_config(
    page_title="今天吃什麼？美食轉盤",
    page_icon="🍱",
    layout="centered"
)

# --- 自定義 CSS (注入美感) ---
st.markdown("""
    <style>
    /* 整體背景色與字體 */
    .stApp {
        background-color: #FDFCF0;
    }
    
    /* 按鈕美化 */
    div.stButton > button:first-child {
        background-color: #FF4B2B;
        color: white;
        border-radius: 20px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #FF416C;
        border: none;
        transform: scale(1.02);
    }
    
    /* 餐廳資訊卡片 */
    .res-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 10px solid #FF4B2B;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 初始化 API ---
api_key = st.secrets["GMAP_API_KEY"]
gmaps = googlemaps.Client(key=api_key)

# --- 側邊欄：設定區 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/706/706164.png", width=100)
    st.title("美食設定")
    mode = st.radio("📍 定位方式", ["目前位置", "自訂地址"])
    radius = st.slider("📏 搜尋範圍 (公尺)", 300, 5000, 1000, 100)
    
    target_lat, target_lng = None, None

    if mode == "目前位置":
        loc = get_geolocation()
        if loc:
            target_lat, target_lng = loc['coords']['latitude'], loc['coords']['longitude']
            st.success("GPS 已就緒")
    else:
        address = st.text_input("🏠 輸入目標區域", placeholder="例如：西門町")
        if address:
            res = gmaps.geocode(address)
            if res:
                target_lat = res[0]['geometry']['location']['lat']
                target_lng = res[0]['geometry']['location']['lng']

# --- 主畫面 ---
st.title("🍜 今天吃什麼？")
st.write("點擊下方按鈕，讓命運決定你的下一餐！")

if target_lat and target_lng:
    # 搜尋按鈕
    if st.button('🔍 搜尋附近美食'):
        with st.spinner('正在尋找好吃的...'):
            res = gmaps.places_nearby(
                location=(target_lat, target_lng),
                radius=radius,
                type='restaurant',
                language='zh-TW'
            )
            
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
            st.toast(f"找到 {len(results)} 家餐廳！")

    # 抽獎與結果
    if 'res_list' in st.session_state and st.session_state['res_list']:
        if st.button('🎰 命運轉盤'):
            st.session_state['selected_res'] = random.choice(st.session_state['res_list'])
            st.balloons()

        if 'selected_res' in st.session_state:
            pick = st.session_state['selected_res']
            
            # 使用卡片式佈局
            st.markdown(f"""
                <div class="res-card">
                    <h2 style='color: #333;'>{pick['名稱']}</h2>
                    <p>⭐ <b>評分：</b>{pick['評價']} ({pick['評論數']} 則評論)</p>
                    <p>📍 <b>地址：</b>{pick['地址']}</p>
                </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])
            with col1:
                st.link_button("🚀 導航前往", pick['地圖連結'], use_container_width=True)
            with col2:
                if st.button("🔄 再抽一次"):
                    st.rerun()

            # 地圖區
            with st.expander("🗺️ 查看地圖預覽", expanded=True):
                st.components.v1.iframe(pick['嵌入連結'], height=400)
else:
    st.info("請在左側選擇定位方式來開始。")
