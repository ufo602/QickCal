from typing import List

import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel

import config


class ParsedOrder(BaseModel):
    start_location: str
    end_location: str
    vehicle: str
    surcharges: List[str]


@st.cache_resource(show_spinner=False)
def _get_client():
    return genai.Client(api_key=config.GEMINI_API_KEY)


def parse_order_text(order_text, vehicle_options, surcharge_options):
    """통화 후 메모한 주문 텍스트에서 출발지/도착지/차종/할증 정보를 추출합니다."""
    system_prompt = (
        "퀵서비스 사무소 직원이 전화 주문을 받은 뒤 남긴 짧은 메모에서 "
        "출발지, 도착지, 차종, 할증 조건을 추출하는 보조 도구다.\n"
        f"차종은 반드시 다음 목록 중 가장 가까운 하나로 골라라: {', '.join(vehicle_options)}.\n"
        f"할증 조건은 반드시 다음 목록에서만 골라라 (해당 없으면 빈 리스트): {', '.join(surcharge_options)}.\n"
        "메모에 없는 정보는 빈 문자열 또는 빈 리스트로 둬라."
    )

    response = _get_client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=order_text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=ParsedOrder,
            temperature=0,
        ),
    )
    return response.parsed
