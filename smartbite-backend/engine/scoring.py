from config.billing_config import CONFIG

def compute_smart_score(distance_km, order_value, demand_level):
    D = 1 / (distance_km + CONFIG.score_distance_epsilon)
    V = order_value / CONFIG.score_value_normaliser
    T = CONFIG.demand_score_multipliers[demand_level]

    score = (
        CONFIG.score_weight_value * V +
        CONFIG.score_weight_distance * D +
        CONFIG.score_weight_demand * (1 / T)
    )

    return round(score, 3)