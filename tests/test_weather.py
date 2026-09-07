from flight_tracker.weather import parse_metar

# Real observations from Dublin, saved so these tests never hit the network.
SOUTHWESTERLY = (
    "METAR EIDW 071630Z 22010KT 180V240 9999 -SHRA FEW006 FEW018CB "
    "BKN045 14/14 Q1011 TEMPO 4000 SHRA"
)
VARIABLE = "METAR EIDW 071630Z VRB03KT 9999 FEW020 12/09 Q1015"
STRONG_WESTERLY = "METAR EIDW 120950Z 27018KT 9999 SCT030 11/06 Q1008 NOSIG"


def test_parses_wind_from_a_real_dublin_metar():
    observation = parse_metar(SOUTHWESTERLY)
    assert observation.wind_dir == 220
    assert observation.wind_speed == 10


def test_keeps_the_raw_text_for_display():
    observation = parse_metar(SOUTHWESTERLY)
    assert observation.raw == SOUTHWESTERLY


def test_variable_wind_has_no_direction():
    observation = parse_metar(VARIABLE)
    assert observation.wind_dir is None
    assert observation.wind_speed == 3


def test_trailing_nosig_group_does_not_break_parsing():
    observation = parse_metar(STRONG_WESTERLY)
    assert observation.wind_dir == 270
    assert observation.wind_speed == 18
