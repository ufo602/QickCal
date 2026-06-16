import requests
import streamlit as st


@st.cache_data(show_spinner=False, ttl=600)
def search_places_kakao(keyword, api_key):
    """카카오 로컬 API로 장소 검색 결과를 반환합니다."""
    url = f"https://dapi.kakao.com/v2/local/search/keyword.json?query={keyword}"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("documents", [])
    except Exception:
        pass
    return None


def get_directions_kakao(start_lon, start_lat, end_lon, end_lat, api_key):
    """카카오 모빌리티 API로 자동차 주행 경로 및 거리를 반환합니다."""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{start_lon},{start_lat}",
        "destination": f"{end_lon},{end_lat}",
        "priority": "RECOMMEND",
    }
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("routes"):
                route = data["routes"][0]
                summary = route["summary"]
                path_coords = []
                for section in route["sections"]:
                    for road in section["roads"]:
                        vertexes = road["vertexes"]
                        for i in range(0, len(vertexes), 2):
                            path_coords.append((vertexes[i + 1], vertexes[i]))
                return {
                    "distance_km": summary["distance"] / 1000,
                    "duration_min": summary["duration"] // 60,
                    "path_coords": path_coords,
                }
    except Exception:
        pass
    return None
