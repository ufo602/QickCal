import config


def get_base_fare(distance_km, vehicle):
    """거리와 차종으로 전국거리운송표에서 고객 청구 기본 요금을 반환합니다."""
    for band in config.FARE_TABLE:
        if distance_km <= band["max_km"]:
            return band["fares"].get(vehicle, 0)
    # 표 최대 거리(500km) 초과 시 마지막 구간 요금 반환
    return config.FARE_TABLE[-1]["fares"].get(vehicle, 0)


def calculate_fares(distance, vehicle, selected_surcharges):
    """전국거리운송표 기준 고객 청구 요금을 계산합니다."""
    # 1. 구간 요금표에서 기본 요금 조회
    base = get_base_fare(distance, vehicle)

    # 2. 할증 적용 (기본 + 할증)
    surcharge_rate = sum(config.SURCHARGE_RATES[c] for c in selected_surcharges)
    surcharge_amount = base * surcharge_rate
    total = int(base + surcharge_amount)

    return {
        "customer": {
            "base": base,
            "surcharge_amount": surcharge_amount,
            "total": total,
            "rate": surcharge_rate,
        },
        "is_negotiable": vehicle in config.NEGOTIABLE_VEHICLES,
        "over_range": distance > config.FARE_TABLE[-1]["max_km"],
    }
