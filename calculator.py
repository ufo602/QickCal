import config


def calculate_fares(distance, vehicle, cargo, selected_surcharges):
    """입력받은 정보를 바탕으로 고객 청구 요금, 실제 원가, 마진을 계산합니다."""
    distance_rounded = round(distance)
    extra_distance = max(0, distance_rounded - config.FREE_DISTANCE)

    # 1. 고객 청구 요금 계산
    base_fare = config.BASE_FARES[vehicle]
    distance_fare = extra_distance * config.COST_PER_KM
    cargo_fare = config.CARGO_FARES[cargo]
    subtotal = base_fare + distance_fare + cargo_fare
    total_surcharge_rate = sum(config.SURCHARGE_RATES[c] for c in selected_surcharges)
    surcharge_amount = subtotal * total_surcharge_rate
    final_total_fare = int(subtotal + surcharge_amount)

    # 2. 실제 운영 요금(기사 지급/원가) 계산
    actual_base_fare = config.ACTUAL_BASE_FARES[vehicle]
    actual_distance_fare = extra_distance * config.ACTUAL_COST_PER_KM
    actual_cargo_fare = config.ACTUAL_CARGO_FARES[cargo]
    actual_subtotal = actual_base_fare + actual_distance_fare + actual_cargo_fare
    actual_total_surcharge_rate = sum(
        config.ACTUAL_SURCHARGE_RATES[c] for c in selected_surcharges
    )
    actual_surcharge_amount = actual_subtotal * actual_total_surcharge_rate
    final_actual_fare = int(actual_subtotal + actual_surcharge_amount)

    # 3. 수익(마진) 계산
    profit = final_total_fare - final_actual_fare

    return {
        "extra_distance": extra_distance,
        "customer": {
            "base": base_fare,
            "dist": distance_fare,
            "cargo": cargo_fare,
            "surcharge_amount": surcharge_amount,
            "total": final_total_fare,
            "rate": total_surcharge_rate,
        },
        "actual": {
            "base": actual_base_fare,
            "dist": actual_distance_fare,
            "cargo": actual_cargo_fare,
            "surcharge_amount": actual_surcharge_amount,
            "total": final_actual_fare,
        },
        "profit": profit,
    }
