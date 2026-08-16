import streamlit as st

# 구글 시트에 저장할 주문 기록 컬럼
ORDER_COLUMNS = [
    "일시", "출발지", "도착지", "거리km", "차종", "구간", "표기준가", "실제청구가", "할증",
]

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@st.cache_resource(show_spinner=False)
def _get_worksheet():
    """구글 시트 워크시트를 반환합니다. (없으면 헤더 생성)"""
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=_SCOPES
    )
    ws = gspread.authorize(creds).open_by_key(st.secrets["GSHEET_ID"]).sheet1

    # 첫 행이 비어 있으면 헤더 작성
    if not ws.acell("A1").value:
        ws.update([ORDER_COLUMNS], range_name="A1", value_input_option="USER_ENTERED")
    return ws


def append_order(record):
    """주문 한 건을 구글 시트에 추가하고 통계 캐시를 비웁니다."""
    ws = _get_worksheet()
    ws.append_row(
        [record.get(c, "") for c in ORDER_COLUMNS],
        value_input_option="USER_ENTERED",
    )
    get_recent_stats.clear()


def _to_int(value):
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


@st.cache_data(show_spinner=False, ttl=60)
def get_recent_stats(band_label, vehicle):
    """같은 구간·차종의 과거 실제 청구가 통계를 반환합니다. (없으면 None)"""
    ws = _get_worksheet()
    prices = []
    for row in ws.get_all_records():
        if str(row.get("구간")) == band_label and str(row.get("차종")) == vehicle:
            price = _to_int(row.get("실제청구가"))
            if price:
                prices.append(price)

    if not prices:
        return None

    recent = prices[-10:]
    return {
        "count": len(prices),
        "avg": round(sum(prices) / len(prices)),
        "min": min(prices),
        "max": max(prices),
        "recent_avg": round(sum(recent) / len(recent)),
    }
