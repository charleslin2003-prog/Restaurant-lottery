import streamlit as st
from streamlit_js_eval import get_geolocation
import googlemaps
import random
import pandas as pd

# 讀取 Secrets
api_key = st.secrets["GMAP_API_KEY"]
gmaps = googlemaps.Client(key=api_key)

st.title("🍴 餐廳隨機抽")

# --- 1. 設定區域 ---
with st.sidebar:
    st.header("設定")
    
    # 功能 1：選擇地點方式
    mode = st.radio("定位方式", ["目前位置", "自訂地址"])
    
    # 功能 2：路程距離滑塊 (公尺)
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
            # 使用 Geocoding API 轉換地址
            geocode_result = gmaps.geocode(address)
            if geocode_result:
                target_lat = geocode_result[0]['geometry']['location']['lat']
                target_lng = geocode_result[0]['geometry']['location']['lng']
                st.success(f"已定位：{address}")

# --- 2. 搜尋與抽獎 ---
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
            # 產生 Google Maps 搜尋連結
            # 格式：https://www.google.com/maps/search/?api=1&query=餐廳名&query_place_id=ID
            place_id = p.get('place_id')
            name = p['name']
            map_url = f"https://www.google.com/maps/search/?api=1&query={name}&query_place_id={place_id}"
            
            results.append({
                '名稱': name,
                '評價': p.get('rating', 0),
                '地址': p.get('vicinity', ''),
                '評論數': p.get('user_ratings_total', 0),
                '地圖連結': map_url
            })
        
        st.session_state['res_list'] = results
        st.write(f"找到 {len(results)} 間餐廳")

    if st.button('🎰 隨機抽一間'):
            pick = random.choice(st.session_state['res_list'])
            st.balloons()
            st.info(f"今天推薦：**{pick['名稱']}**")
            st.write(f"⭐ 評價：{pick['評價']} ({pick['評論數']} 則)")
            st.write(f"📍 地址：{pick['地址']}")
            
            # 加上按鈕跳轉至 Google Maps
            st.link_button("🚀 帶我去這間餐廳", pick['地圖連結'])
else:
    st.warning("請先完成定位（開啟 GPS 或輸入地址）。")
