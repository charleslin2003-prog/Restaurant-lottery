import streamlit as st
from streamlit_js_eval import get_geolocation
import googlemaps
import random
import pandas as pd

st.set_page_config(page_title="午餐吃什麼？", layout="centered")

# 設定 Google Maps API (建議放在 Secrets 中)
# st.secrets["GMAP_API_KEY"]
gmaps = googlemaps.Client(key='YOUR_GOOGLE_MAPS_API_KEY')

st.title("🍴 周圍餐廳隨機抽")

# 1. 取得使用者經緯度
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lng = loc['coords']['longitude']
    
    if st.button('搜尋附近餐廳'):
        # 2. 呼叫 Places API 搜尋 500 公尺內的餐廳
        places_result = gmaps.places_nearby(
            location=(lat, lng),
            radius=500,
            type='restaurant',
            language='zh-TW'
        )
        
        restaurants = []
        for place in places_result.get('results', []):
            restaurants.append({
                '名稱': place['name'],
                '評價': place.get('rating', '無'),
                '地址': place.get('vicinity', '未知'),
                '總評分數': place.get('user_ratings_total', 0)
            })
        
        if restaurants:
            df = pd.DataFrame(restaurants)
            st.session_state['restaurants'] = restaurants
            st.success(f"找到 {len(restaurants)} 家附近的餐廳！")
        else:
            st.warning("附近沒有找到餐廳。")

# 3. 轉盤抽獎功能
if 'restaurants' in st.session_state:
    res_list = st.session_state['restaurants']
    
    if st.button('🎰 開始抽獎'):
        selected = random.choice(res_list)
        
        # 顯示結果
        st.balloons()
        st.subheader(f"今天就吃：{selected['名稱']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Google 評分", f"⭐ {selected['評價']}")
        with col2:
            st.write(f"📍 地址：{selected['地址']}")
            st.write(f"💬 評論數：{selected['總評分數']}")
            
    # 顯示清單備選
    with st.expander("查看完整清單"):
        st.table(pd.DataFrame(res_list))
else:
    st.info("請允許瀏覽器定位並點擊搜尋按鈕。")
