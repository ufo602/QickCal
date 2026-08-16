import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import urllib.parse

import config
from api_services import search_places_kakao, get_directions_kakao
from calculator import calculate_fares
from ai_parser import parse_order_text

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
# [페이지 설정 및 디자인]
# =====================================================================
st.set_page_config(page_title="퀵 서비스 요금 계산기", page_icon="🚚", layout="centered")

st.markdown(
    """
    <style>
    html { font-size: 19px; }
    h1 { font-size: 2.1rem !important; }
    h3 { font-size: 1.4rem !important; }
    p, label, .stMarkdown { font-size: 1.05rem !important; }

    .stButton button {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: 0.8rem 1.2rem !important;
        border-radius: 12px !important;
    }
    .stSelectbox label, .stNumberInput label, .stRadio label,
    .stCheckbox label, .stTextInput label {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] summary {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }

    .fare-hero {
        background: linear-gradient(135deg, #FF6B35, #FF9558);
        border-radius: 18px;
        padding: 30px 20px;
        text-align: center;
        color: white;
        margin: 8px 0 16px 0;
        box-shadow: 0 6px 16px rgba(255, 107, 53, 0.30);
    }
    .fare-hero .label { font-size: 1.15rem; opacity: 0.95; font-weight: 600; }
    .fare-hero .amount { font-size: 3.2rem; font-weight: 800; letter-spacing: -1px; line-height: 1.2; }
    .fare-hero .amount span { font-size: 1.4rem; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚚 퀵 서비스 요금 계산기")
st.markdown("출발지·도착지만 검색하면 거리부터 요금까지 한 번에 계산됩니다.")

api_ready = config.KAKAO_API_KEY.strip() and config.KAKAO_API_KEY != "여기에_API_키를_입력하세요"
if not api_ready:
    st.error("⚠️ 카카오 REST API 키가 설정되지 않았습니다. Secrets에 `KAKAO_API_KEY`를 설정해 주세요.")

ai_ready = bool(config.ANTHROPIC_API_KEY.strip())

QUICK_VEHICLES = ["오토바이", "다마스", "라보", "1톤"]
ALL_VEHICLES = list(config.FARE_TABLE[0]["fares"].keys())

# =====================================================================
# [0. 통화 후 빠른 입력 (AI 자동 분석)]
# =====================================================================
with st.container(border=True):
    st.markdown("### 🤖 0. 통화 후 빠른 입력 (선택)")
    st.caption("통화하면서 메모한 내용을 그대로 적으면 출발지·도착지·차종·할증을 자동으로 채워드려요.")
    order_text = st.text_area(
        "주문 메모",
        placeholder="예: 강남역에서 잠실역, 1톤 트럭, 비 와서 급하게 보내야 해요",
        label_visibility="collapsed",
    )
    if st.button("🤖 AI로 자동 입력", use_container_width=True, disabled=not ai_ready):
        if not order_text.strip():
            st.warning("메모를 입력해 주세요.")
        else:
            with st.spinner("주문 내용을 분석하는 중입니다..."):
                try:
                    parsed = parse_order_text(order_text, ALL_VEHICLES, list(config.SURCHARGE_RATES.keys()))
                except Exception:
                    parsed = None

            if parsed is None:
                st.error("AI 분석에 실패했습니다. 직접 입력해 주세요.")
            else:
                if parsed.start_location:
                    st.session_state["start_keyword"] = parsed.start_location
                if parsed.end_location:
                    st.session_state["end_keyword"] = parsed.end_location
                if parsed.vehicle in QUICK_VEHICLES:
                    st.session_state["vehicle_select"] = parsed.vehicle
                    st.session_state["big_vehicle_checkbox"] = False
                elif parsed.vehicle in ALL_VEHICLES:
                    st.session_state["big_vehicle_select"] = parsed.vehicle
                    st.session_state["big_vehicle_checkbox"] = True
                st.session_state["surcharge_pills"] = [
                    s for s in parsed.surcharges if s in config.SURCHARGE_RATES
                ]
                st.success("출발지·도착지·차종·할증을 자동으로 채웠습니다. 아래에서 확인해 주세요.")
    if not ai_ready:
        st.caption("⚠️ AI 자동 입력을 사용하려면 Secrets에 `ANTHROPIC_API_KEY`를 설정해 주세요.")

# =====================================================================
# [1. 지도 길찾기 및 거리 자동 계산]
# =====================================================================
with st.container(border=True):
    st.markdown("### 📍 1. 거리 확인")

    col_addr1, col_addr2 = st.columns(2)
    start_loc = None
    end_loc = None

    with col_addr1:
        start_keyword = st.text_input("출발지", placeholder="예: 강남역, 서울시청", key="start_keyword")
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
        end_keyword = st.text_input("도착지", placeholder="예: 부산역, 광화문", key="end_keyword")
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
                    st.success(f"운행 거리 **{route_data['distance_km']:.1f} km** · 소요 시간 약 **{route_data['duration_min']}분**")
                else:
                    st.error("자동차 길찾기 경로를 가져올 수 없습니다. 지명이나 API 키를 다시 확인해 주세요.")

    if st.session_state.map_obj:
        st_folium(st.session_state.map_obj, width=None, height=350, returned_objects=[])

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
            <button style="width:100%;padding:14px;background-color:#03C75A;color:white;
            border:none;border-radius:12px;font-size:1.1rem;font-weight:bold;cursor:pointer;margin-top:10px;">
            🟢 네이버 지도로 실제 주행 경로 확인하기
            </button></a>''',
            unsafe_allow_html=True,
        )

# =====================================================================
# [2. 운송 정보 입력]
# =====================================================================
with st.container(border=True):
    st.markdown("### 🚚 2. 차종 & 할증 선택")

    vehicle = st.segmented_control(
        "운송 수단", options=QUICK_VEHICLES, default=QUICK_VEHICLES[0], key="vehicle_select"
    )

    with st.expander(
        "🚛 더 큰 차량이 필요하신가요? (1.4톤 ~ 25톤)",
        expanded=st.session_state.get("big_vehicle_checkbox", False),
    ):
        big_vehicle = st.selectbox(
            "대형 차량 선택", [v for v in ALL_VEHICLES if v not in QUICK_VEHICLES], key="big_vehicle_select"
        )
        if st.checkbox(f"'{big_vehicle}'으로 계산하기", key="big_vehicle_checkbox"):
            vehicle = big_vehicle

    vehicle = vehicle or QUICK_VEHICLES[0]

    distance = st.number_input(
        "운행 거리 (km)",
        min_value=0.0,
        value=float(st.session_state.calc_distance),
        step=0.5,
        format="%.1f",
    )

    selected_surcharges = st.pills(
        "할증 조건 (해당 시 선택, 다중 선택 가능)",
        options=list(config.SURCHARGE_RATES.keys()),
        selection_mode="multi",
        key="surcharge_pills",
    )
    selected_surcharges = selected_surcharges or []

# =====================================================================
# [3. 요금 산출 결과]
# =====================================================================
st.markdown("### 💰 3. 요금 산출 결과")

res = calculate_fares(distance, vehicle, selected_surcharges)

if res["over_range"]:
    st.warning(f"⚠️ 입력 거리({distance:.1f}km)가 요금표 최대 구간(500km)을 초과합니다. 500km 기준 요금으로 표시됩니다.")

if res["is_negotiable"]:
    st.info(f"💬 **{vehicle}**는 표시 요금이 최저가입니다. 실제 요금은 화물 상태에 따라 협의하세요.")

if selected_surcharges:
    st.info(f"💡 적용된 할증: {', '.join(selected_surcharges)} (총 +{int(res['customer']['rate'] * 100)}%)")

st.markdown(
    f"""
    <div class="fare-hero">
        <div class="label">고객 청구 요금</div>
        <div class="amount">{res['customer']['total']:,}<span> 원</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("🔍 요금 세부 내역 보기"):
    st.write(f"- 구간 기본료: {res['customer']['base']:,} 원")
    st.write(f"- 할증 금액: {int(res['customer']['surcharge_amount']):,} 원")
    st.write(f"- **합계: {res['customer']['total']:,} 원**")

# =====================================================================
# [4. 전국거리운송표 전체 보기 (요금 참고)]
# =====================================================================
# 요금표 이미지의 실제 거리 구간 라벨 (config.FARE_TABLE 순서와 1:1 대응)
FARE_BAND_LABELS = [
    "0~6km", "6.1~10km", "10.1~18km", "18.1~21.9km", "22~30km",
    "30.1~36km", "36.1~42km", "42.1~47.4km", "47.5~51km", "51.1~57km",
    "57.1~65.9km", "66~70.9km", "71~81km", "81.1~87km", "87.1~96km",
    "96.1~112km", "112.1~121km", "121.1~136km", "136.1~150km", "150.1~160km",
    "161~175km", "175.1~185km", "186~200km", "201~210km", "211~220km",
    "221~235km", "236~250km", "251~260km", "260.1~276km", "276.1~285km",
    "286~300km", "301~325km", "326~335km", "335.1~350km", "350.1~365km",
    "366~376km", "376.1~400km", "401~430km", "431~450km", "451~500km",
]


@st.cache_data(show_spinner=False)
def build_fare_table_df():
    """전국거리운송표를 참고용 데이터프레임으로 만듭니다. (협의 차종은 요금 뒤 '~')"""
    rows = []
    for label, band in zip(FARE_BAND_LABELS, config.FARE_TABLE):
        row = {"거리": label}
        for veh, price in band["fares"].items():
            row[veh] = f"{price:,}~" if veh in config.NEGOTIABLE_VEHICLES else f"{price:,}"
        rows.append(row)
    return pd.DataFrame(rows).set_index("거리")


with st.container(border=True):
    st.markdown("### 📋 4. 전국거리운송표 (요금 참고)")
    with st.expander("📋 차종·거리별 요금표 전체 보기"):
        st.caption("단위: 원 · 요금 뒤 '~'는 최저가로 화물 상태에 따라 협의 가능합니다.")
        st.dataframe(build_fare_table_df(), use_container_width=True, height=430)
        st.markdown(
            """
            **참고사항**
            - 탑차·윙바디·리프트 차량은 1~3만원 추가됩니다.
            - 화물 특성(이사짐 등)·작업 조건·수작업·야간 운송·지역 특성(강원도·서울)에 따라 요금이 변경될 수 있습니다.
            - 상·하차 시간 지연, 천재지변·악천후, 차량 정체·퇴근 시간에는 추가 요금이 발생할 수 있습니다.
            """
        )
