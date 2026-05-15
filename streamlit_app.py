import streamlit as st
from streamlit_js_eval import get_geolocation
import googlemaps
import random
import pandas as pd

# 1. 讀取 Secrets
api_key = st.secrets["GMAP_API_KEY"]
gmaps = googlemaps.Client(key=api_key)

st.title("🍴 餐廳隨機抽")

# --- 2. 設定區域 (側邊欄) ---
with st.sidebar:
    st.header("設定")
    mode = st.radio("定位方式", ["目前位置", "自訂地址"])
    radius = st.slider("搜尋範圍 (公尺)", min_value=300, max_value=5000, value=1000, step=100)
    
    target_lat, target_lng = None, None

    if mode == "目前位置":
        loc = get_geolocation()
        if loc:
            target_lat = loc['coords']['latitude']
            target_lng = loc['coords']['longitude']
            st.success("已取得 GPS 定位")
    else:
        address = st.text_input("輸入地址或地標", placeholder="例如：台北 101")
        if address:
            geocode_result = gmaps.geocode(address)
            if geocode_result:
                target_lat = geocode_result[0]['geometry']['location']['lat']
                target_lng = geocode_result[0]['geometry']['location']['lng']
                st.success(f"已定位：{address}")

# --- 3. 搜尋與抽獎 ---
if target_lat and target_lng:
    if st.button('🔍 搜尋餐廳'):
        res = gmaps.places_nearby(
            location=(target_lat, target_lng),
            radius=radius,
            type='restaurant',
            language='zh-TW'
        )
        
        results = []
        for p in res.get('results', []):
            name = p['name']
            place_id = p.get('place_id')
            # 建立地圖連結
            map_url = f"https://www.google.com/maps/search/?api=1&query={name}&query_place_id={place_id}"
            # 建立嵌入地圖用的 URL (使用 Embed API 格式)
            embed_url = f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{place_id}"
            
            results.append({
                '名稱': name,
                '評價': p.get('rating', 0),
                '地址': p.get('vicinity', ''),
                '評論數': p.get('user_ratings_total', 0),
                '地圖連結': map_url,
                '嵌入連結': embed_url
            })
        
        st.session_state['res_list'] = results
        st.write(f"找到 {len(results)} 間餐廳")

    if 'res_list' in st.session_state and st.session_state['res_list']:
        if st.button('🎰 隨機抽一間'):
            pick = random.choice(st.session_state['res_list'])
            st.session_state['selected_res'] = pick
            st.balloons()

        # 顯示抽中結果
        if 'selected_res' in st.session_state:
            pick = st.session_state['selected_res']
            st.info(f"今天推薦：**{pick['名稱']}**")
            st.write(f"⭐ 評價：{pick['評價']} ({pick['評論數']} 則)")
            st.write(f"📍 地址：{pick['地址']}")
            st.link_button("🚀 帶我去這間餐廳 (開啟新分頁)", pick['地圖連結'])
            
            # --- 功能新增：黃色區域嵌入地圖 ---
            st.write("---")
            st.subheader("📍 地點預覽")
            st.components.v1.iframe(pick['嵌入連結'], height=450)

else:
    st.warning("請先完成定位（開啟 GPS 或輸入地址）。")
