import config


def get_base_fare(distance_km, vehicle):
    """거리와 차종으로 전국거리운송표에서 고객 청구 기본 요금을 반환합니다."""
    for band in config.FARE_TABLE:
        if distance_km <= band["max_km"]:
            return band["fares"].get(vehicle, 0)
    # 표 최대 거리(220km) 초과 시 마지막 구간 요금 반환
    return config.FARE_TABLE[-1]["fares"].get(vehicle, 0)


def calculate_fares(distance, vehicle, selected_surcharges):
    """고객 청구 요금, 기사 지급 원가, 사무소 수익을 계산합니다."""
    # 1. 구간 요금표에서 기본 요금 조회
    base_customer = get_base_fare(distance, vehicle)

    # 2. 고객 청구 요금 (기본 + 할증)
    surcharge_rate = sum(config.SURCHARGE_RATES[c] for c in selected_surcharges)
    customer_surcharge = base_customer * surcharge_rate
    total_customer = int(base_customer + customer_surcharge)

    # 3. 기사 지급 원가 (고객 요금의 80%)
    base_driver = int(base_customer * config.DRIVER_RATIO)
    driver_surcharge = base_driver * surcharge_rate
    total_driver = int(base_driver + driver_surcharge)

    # 4. 사무소 수익(마진)
    profit = total_customer - total_driver

    return {
        "customer": {
            "base": base_customer,
            "surcharge_amount": customer_surcharge,
            "total": total_customer,
            "rate": surcharge_rate,
        },
        "actual": {
            "base": base_driver,
            "surcharge_amount": driver_surcharge,
            "total": total_driver,
        },
        "profit": profit,
        "is_negotiable": vehicle in config.NEGOTIABLE_VEHICLES,
        "over_range": distance > config.FARE_TABLE[-1]["max_km"],
    }
