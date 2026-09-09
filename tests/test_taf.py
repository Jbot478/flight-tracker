from datetime import datetime, timezone

from flight_tracker.taf import build_timeline, parse_taf

# A real Dublin TAF: base westerly backing round to the southwest overnight.
DUBLIN_TAF = (
    "TAF EIDW 091100Z 0912/1012 28010KT 9999 FEW020 SCT030 "
    "BECMG 0914/0916 24007KT "
    "BECMG 0917/0919 21007KT "
    "BECMG 1001/1003 16008KT "
    "BECMG 1007/1009 21013KT "
    "BECMG 1009/1011 22015G26KT "
    "TEMPO 1010/1012 -RA BKN012"
)
NOW_DUBLIN = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)

# A messier one: a TEMPO gust, a PROB30 TEMPO, and a TEMPO with no wind at all.
MESSY_TAF = (
    "TAF EIDW 121100Z 1212/1312 25012KT 9999 SCT025 "
    "TEMPO 1212/1218 26018G30KT "
    "BECMG 1218/1221 30008KT "
    "PROB30 TEMPO 1222/1302 32015G25KT SHRA "
    "BECMG 1303/1306 09006KT "
    "TEMPO 1306/1312 4000 -RA BKN008"
)
NOW_MESSY = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)


def test_reads_the_validity_window():
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    assert forecast.valid_from == datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
    assert forecast.valid_to == datetime(2026, 9, 10, 12, tzinfo=timezone.utc)


def test_base_wind_is_the_first_period():
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    first = forecast.periods[0]
    assert first.wind_dir == 280
    assert first.wind_speed == 10


def test_becmg_takes_effect_at_the_end_of_its_window():
    # "BECMG 0914/0916 24007KT" - the change is complete by 16:00, not 14:00.
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    second = forecast.periods[1]
    assert second.start == datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
    assert second.wind_dir == 240


def test_gust_is_ignored_and_only_the_steady_wind_is_kept():
    # "22015G26KT" gusting 26: we forecast on the steady 15.
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    last = forecast.periods[-1]
    assert last.wind_dir == 220
    assert last.wind_speed == 15


def test_tempo_and_prob_groups_do_not_create_periods():
    # Base plus two BECMG groups. The TEMPO gust, the PROB30 TEMPO and the
    # rain-only TEMPO must all be skipped.
    forecast = parse_taf(MESSY_TAF, now=NOW_MESSY)
    assert len(forecast.periods) == 3
    assert all(period.wind_speed != 18 for period in forecast.periods)


def test_timeline_covers_twenty_four_hours():
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    timeline = build_timeline(forecast, now=NOW_DUBLIN)
    assert len(timeline) == 24
    assert timeline[0].time == NOW_DUBLIN


def test_raw_timeline_holds_the_main_pair_through_light_shifts():
    # 210 at 7 kt no longer sends Dublin to the crosswind runway: it stays
    # on 28. Only the overnight southerly turns the airport round, to 10.
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    timeline = build_timeline(forecast, now=NOW_DUBLIN, hysteresis=False)

    assert timeline[7].config == "28"     # 19:00, backed to 210 at 7 kt
    assert timeline[14].config == "28"    # 02:00, still westerly enough
    assert timeline[15].config == "10"    # 03:00, 160 at 8 kt
    assert timeline[-1].config == "28"    # 11:00, back to 220


def test_hysteresis_delays_the_overnight_changeover():
    # The raw rule switches the moment the wind does; the airport takes an
    # hour to be convinced.
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    timeline = build_timeline(forecast, now=NOW_DUBLIN)

    assert timeline[15].config == "28"    # 03:00, case still building
    assert timeline[16].config == "10"    # 04:00, switched


def test_hysteresis_also_delays_the_switch_back():
    forecast = parse_taf(DUBLIN_TAF, now=NOW_DUBLIN)
    timeline = build_timeline(forecast, now=NOW_DUBLIN)

    assert timeline[21].config == "10"    # 09:00, wind has veered but we hold
    assert timeline[22].config == "28"    # 10:00, switched back


def test_raw_messy_taf_swings_east_in_the_morning():
    forecast = parse_taf(MESSY_TAF, now=NOW_MESSY)
    timeline = build_timeline(forecast, now=NOW_MESSY, hysteresis=False)

    assert timeline[0].config == "28"     # 12:00, 250 degrees
    assert timeline[18].config == "10"    # 06:00 next day, 090 degrees


def test_smoothed_messy_taf_lags_the_morning_swing_by_an_hour():
    forecast = parse_taf(MESSY_TAF, now=NOW_MESSY)
    timeline = build_timeline(forecast, now=NOW_MESSY)

    assert timeline[18].config == "28"    # 06:00, case building
    assert timeline[19].config == "10"    # 07:00, switched
