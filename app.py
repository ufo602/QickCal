import streamlit as st
import folium
from streamlit_folium import st_folium
import urllib.parse

import config
from api_services import search_places_kakao, get_directions_kakao
from calculator import calculate_fares

# =====================================================================
# [상태 저장소 (Session State)]
# =====================================================================
if "calc_distance" not in st.session_state:
    st.session_state.calc_distance = 5.0
if "map_obj" not in st.session_state:
    st.session_state.map_obj = None
if "start_info" not in st.session_state:
    st.session_state.start_info = None
if "end_info" not in st.session_state:
    st.session_state.end_info = None

# =====================================================================
# [사용자 인터페이스 (UI) 화면 구성]
# =====================================================================
st.set_page_config(page_title="퀵 서비스 요금 계산기", page_icon="🚚", layout="centered")
st.title("🚚 퀵 서비스 요금 & 길찾기 계산기")
st.markdown("출발/도착지를 검색하여 거리를 확인하고, 고객 청구 요금과 실제 운영 수익을 계산해 보세요.")

api_ready = config.KAKAO_API_KEY.strip() and config.KAKAO_API_KEY != "여기에_API_키를_입력하세요"
if not api_ready:
    st.error("⚠️ 카카오 REST API 키가 설정되지 않았습니다. 환경변수 `KAKAO_API_KEY`를 설정해 주세요.")

st.divider()

# --- 길찾기 및 지도 영역 ---
st.subheader("📍 1. 지도 길찾기 및 거리 자동 계산")

col_addr1, col_addr2 = st.columns(2)
start_loc = None
end_loc = None

with col_addr1:
    start_keyword = st.text_input("출발지 검색어 (입력 후 Enter)", placeholder="예: 강남역, 서울시청")
    if start_keyword and api_ready:
        start_res = search_places_kakao(start_keyword, config.KAKAO_API_KEY)
        if start_res:
            start_options = {
                f"{doc['place_name']} ({doc.get('road_address_name') or doc.get('address_name')})": doc
                for doc in start_res[:5]
            }
            selected_start = st.selectbox("✔️ 정확한 출발지 선택", list(start_options.keys()))
            start_loc = start_options[selected_start]
        else:
            st.warning(f"'{start_keyword}' 검색 결과가 없습니다.")

with col_addr2:
    end_keyword = st.text_input("도착지 검색어 (입력 후 Enter)", placeholder="예: 부산역, 광화문")
    if end_keyword and api_ready:
        end_res = search_places_kakao(end_keyword, config.KAKAO_API_KEY)
        if end_res:
            end_options = {
                f"{doc['place_name']} ({doc.get('road_address_name') or doc.get('address_name')})": doc
                for doc in end_res[:5]
            }
            selected_end = st.selectbox("✔️ 정확한 도착지 선택", list(end_options.keys()))
            end_loc = end_options[selected_end]
        else:
            st.warning(f"'{end_keyword}' 검색 결과가 없습니다.")

# --- 경로 확인 및 지도 생성 ---
if start_loc and end_loc:
    if st.button("🗺 경로 확인 및 요금 자동 계산", use_container_width=True):
        with st.spinner("카카오 내비게이션에서 실제 주행 경로를 가져오는 중입니다..."):
            start_lon, start_lat = float(start_loc["x"]), float(start_loc["y"])
            end_lon, end_lat = float(end_loc["x"]), float(end_loc["y"])
            route_data = get_directions_kakao(start_lon, start_lat, end_lon, end_lat, config.KAKAO_API_KEY)

            if route_data:
                st.session_state.calc_distance = route_data["distance_km"]
                center_lat = (start_lat + end_lat) / 2
                center_lon = (start_lon + end_lon) / 2
                m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
                folium.Marker((start_lat, start_lon), tooltip="출발지", icon=folium.Icon(color="green", icon="play")).add_to(m)
                folium.Marker((end_lat, end_lon), tooltip="도착지", icon=folium.Icon(color="red", icon="stop")).add_to(m)
                folium.PolyLine(locations=route_data["path_coords"], color="blue", weight=5, opacity=0.8).add_to(m)
                st.session_state.map_obj = m
                st.session_state.start_info = {"lat": start_lat, "lon": start_lon, "name": start_loc["place_name"]}
                st.session_state.end_info = {"lat": end_lat, "lon": end_lon, "name": end_loc["place_name"]}
                st.success(f"경로 탐색 완료! 운행 거리 **{route_data['distance_km']:.1f} km**, 소요 시간 약 **{route_data['duration_min']}분**")
            else:
                st.error("자동차 길찾기 경로를 가져올 수 없습니다. 지명이나 API 키를 다시 확인해 주세요.")

if st.session_state.map_obj:
    st_folium(st.session_state.map_obj, width=700, height=400, returned_objects=[])

if st.session_state.start_info and st.session_state.end_info:
    start, end = st.session_state.start_info, st.session_state.end_info
    start_enc = urllib.parse.quote(start["name"])
    end_enc = urllib.parse.quote(end["name"])
    naver_url = (
        f"https://map.naver.com/p/directions/"
        f"{start['lon']},{start['lat']},{start_enc}/"
        f"{end['lon']},{end['lat']},{end_enc}/-/car"
    )
    st.markdown(
        f'''<a href="{naver_url}" target="_blank" style="text-decoration: none;">
        <button style="width:100%;padding:12px;background-color:#03C75A;color:white;
        border:none;border-radius:8px;font-size:16px;font-weight:bold;cursor:pointer;margin-top:10px;">
        🟢 네이버 지도로 실제 주행 경로 및 시간 확인하기
        </button></a>''',
        unsafe_allow_html=True,
    )

st.divider()

# --- 운송 정보 입력 영역 ---
st.subheader("📦 2. 운송 상세 정보 입력")
col1, col2 = st.columns(2)

VEHICLES = list(config.FARE_TABLE[0]["fares"].keys())

with col1:
    vehicle = st.selectbox("운송 수단 선택", VEHICLES)
    distance = st.number_input(
        "운행 거리 (km)",
        min_value=0.0,
        value=float(st.session_state.calc_distance),
        step=0.5,
        format="%.1f",
    )

with col2:
    st.write("할증 조건 (해당 시 체크)")
    selected_surcharges = [cond for cond in config.SURCHARGE_RATES.keys() if st.checkbox(cond)]

st.divider()

# --- 요금 산출 결과 ---
st.subheader("💰 요금 산출 결과")
res = calculate_fares(distance, vehicle, selected_surcharges)

if res["over_range"]:
    st.warning(f"⚠️ 입력 거리({distance:.1f}km)가 요금표 최대 구간(500km)을 초과합니다. 500km 기준 요금으로 표시됩니다.")

if res["is_negotiable"]:
    st.info(f"💬 **{vehicle}**는 표시 요금이 최저가입니다. 실제 요금은 화물 상태에 따라 협의하세요.")

if selected_surcharges:
    st.info(f"💡 적용된 할증: {', '.join(selected_surcharges)} (총 +{int(res['customer']['rate'] * 100)}%)")

summary_col1, summary_col2, summary_col3 = st.columns(3)
with summary_col1:
    st.success(f"**고객 청구 요금**\n### {res['customer']['total']:,} 원")
with summary_col2:
    st.warning(f"**기사 지급 요금(원가)**\n### {res['actual']['total']:,} 원")
with summary_col3:
    st.info(f"**사무소 수익(마진)**\n### {res['profit']:,} 원")

with st.expander("🔍 항목별 세부 내역 보기"):
    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        st.markdown("**[청구 요금 내역]**")
        st.write(f"- 구간 기본료: {res['customer']['base']:,} 원")
        st.write(f"- 할증 금액: {int(res['customer']['surcharge_amount']):,} 원")
        st.write(f"- **합계: {res['customer']['total']:,} 원**")
    with detail_col2:
        st.markdown("**[운영 원가 내역]**")
        st.write(f"- 구간 기본료: {res['actual']['base']:,} 원")
        st.write(f"- 할증 금액: {int(res['actual']['surcharge_amount']):,} 원")
        st.write(f"- **합계: {res['actual']['total']:,} 원**")
