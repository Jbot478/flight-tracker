from flight_tracker.runway import apply_hysteresis, headwind, infer_config


def test_clear_westerly_gives_28():
    assert infer_config(270, 15) == "28"


def test_clear_easterly_gives_10():
    assert infer_config(90, 12) == "10"


def test_northerly_gives_34_not_10_or_28():
    # The case that matters: 030 is nearest 340, so the crosswind runway wins.
    assert infer_config(30, 10) == "34"


def test_southerly_gives_16():
    assert infer_config(160, 12) == "16"


def test_light_wind_is_uncertain():
    assert infer_config(270, 3) == "uncertain"


def test_variable_wind_is_uncertain():
    assert infer_config(None, 8) == "uncertain"


def test_headwind_is_full_strength_straight_down_the_runway():
    assert round(headwind(280, 10, "28")) == 10


def test_headwind_is_negative_when_the_wind_is_behind_you():
    assert headwind(100, 10, "28") < 0


def test_light_crosswind_shift_does_not_move_the_airport():
    # 210 at 7 kt gains runway 16 only about 2 knots of headwind over 28.
    # Not worth a changeover, so we hold 28 all the way through.
    winds = [(280, 10)] * 3 + [(210, 7)] * 5
    assert apply_hysteresis(winds) == ["28"] * 8


def test_a_real_wind_shift_does_move_the_airport():
    # 160 at 8 kt leaves runway 28 with a tailwind. That one is genuine.
    winds = [(280, 10)] * 2 + [(160, 8)] * 4
    assert apply_hysteresis(winds)[-1] == "16"


def test_changeover_lags_by_the_persistence_window():
    # The case builds for two hours before the airport actually swaps.
    winds = [(280, 10)] * 2 + [(160, 8)] * 4
    assert apply_hysteresis(winds) == ["28", "28", "28", "16", "16", "16"]


def test_a_single_hour_blip_is_ignored():
    winds = [(280, 10), (280, 10), (160, 10), (280, 10), (280, 10)]
    assert apply_hysteresis(winds) == ["28"] * 5


def test_uncertain_hours_hold_the_current_config():
    winds = [(280, 10), (None, 3), (None, 3), (280, 10)]
    assert apply_hysteresis(winds) == ["28"] * 4


def test_an_uncertain_start_adopts_the_first_real_reading():
    winds = [(None, 3), (280, 10)]
    assert apply_hysteresis(winds) == ["uncertain", "28"]
