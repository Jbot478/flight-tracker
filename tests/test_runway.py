from flight_tracker.runway import infer_config


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
