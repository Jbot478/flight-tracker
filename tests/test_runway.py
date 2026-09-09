from flight_tracker.runway import (
    apply_hysteresis,
    crosswind,
    headwind,
    infer_config,
    infer_config_nearest,
)


def test_clear_westerly_gives_28():
    assert infer_config(270, 15) == "28"


def test_clear_easterly_gives_10():
    assert infer_config(90, 12) == "10"


def test_light_northerly_stays_on_the_main_pair():
    # 030 at 10 kt puts only about 9 kt across the parallel runways - well
    # inside limits - so Dublin stays on them rather than using 34.
    assert infer_config(30, 10) == "10"


def test_light_southerly_stays_on_the_main_pair():
    assert infer_config(160, 12) == "10"


def test_strong_crosswind_forces_the_crosswind_runway():
    # 010 at 35 kt is almost square across 10/28. Now 34 earns its place.
    assert infer_config(10, 35) == "34"


def test_strong_southerly_crosswind_gives_16():
    assert infer_config(190, 35) == "16"


def test_light_wind_is_uncertain():
    assert infer_config(270, 3) == "uncertain"


def test_variable_wind_is_uncertain():
    assert infer_config(None, 8) == "uncertain"


def test_the_old_nearest_heading_rule_is_still_available():
    # Kept for comparison: this is the rule that over-used 16 and 34.
    assert infer_config_nearest(30, 10) == "34"
    assert infer_config_nearest(160, 12) == "16"


def test_headwind_is_full_strength_straight_down_the_runway():
    assert round(headwind(280, 10, "28")) == 10


def test_headwind_is_negative_when_the_wind_is_behind_you():
    assert headwind(100, 10, "28") < 0


def test_crosswind_is_full_strength_square_across_the_runway():
    assert round(crosswind(10, 20, "28")) == 20


def test_light_crosswind_shift_does_not_move_the_airport():
    winds = [(280, 10)] * 3 + [(210, 7)] * 5
    assert apply_hysteresis(winds) == ["28"] * 8


def test_a_real_wind_shift_does_move_the_airport():
    # 160 at 8 kt leaves runway 28 with a tailwind, so 10 is the answer.
    winds = [(280, 10)] * 2 + [(160, 8)] * 4
    assert apply_hysteresis(winds)[-1] == "10"


def test_changeover_lags_by_the_persistence_window():
    winds = [(280, 10)] * 2 + [(160, 8)] * 4
    assert apply_hysteresis(winds) == ["28", "28", "28", "10", "10", "10"]


def test_a_single_hour_blip_is_ignored():
    winds = [(280, 10), (280, 10), (160, 10), (280, 10), (280, 10)]
    assert apply_hysteresis(winds) == ["28"] * 5


def test_uncertain_hours_hold_the_current_config():
    winds = [(280, 10), (None, 3), (None, 3), (280, 10)]
    assert apply_hysteresis(winds) == ["28"] * 4


def test_an_uncertain_start_adopts_the_first_real_reading():
    winds = [(None, 3), (280, 10)]
    assert apply_hysteresis(winds) == ["uncertain", "28"]
