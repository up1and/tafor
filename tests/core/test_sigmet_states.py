"""Direct tests for tafor/core/sigmet/states.py.

The state classes had no direct coverage before this file: composeMessage /
isAcceptable / clear were only exercised through the widget tests. This file
pins the current behavior -- including the literal {location} placeholders
composeMessage emits -- so the planned composeMessage(fir, locations) surgery
shows up as diffs here first. Quirks pinned on purpose carry a comment.
"""

import pytest


from tafor.core.sigmet.states import (
    BaseState,
    SigmetAshState,
    SigmetCancelState,
    SigmetCustomState,
    SigmetGeneralState,
    SigmetHeaderState,
    SigmetTyphoonState,
)

FIR = 'ZJSA'
HEADER_LINE = 'ZJSA SIGMET 2 VALID 100930/101430 ZJHK-'
HEADER_FIELDS = ['area', 'sign', 'sequence', 'beginningTime', 'endingTime', 'icao']


def header(**fields):
    state = SigmetHeaderState()
    state.area = 'ZJSA'
    state.sign = 'SIGMET'
    state.sequence = '2'
    state.beginningTime = '100930'
    state.endingTime = '101430'
    state.icao = 'ZJHK'
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def general(**fields):
    state = SigmetGeneralState('KMH')
    state.header = header()
    state.description = 'SEV'
    state.phenomenon = 'TS'
    state.comeFrom = 'OBS'
    state.observedTime = '100800'
    state.flightLevelBase = '80'
    state.flightLevelTop = '120'
    state.direction = 'NE'
    state.speed = '25'
    state.intensityChange = 'NC'
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def typhoon(**fields):
    state = SigmetTyphoonState('KMH')
    state.header = header()
    state.phenomenon = 'TC'
    state.name = 'SALLY'
    state.currentLatitude = 'N1800'
    state.currentLongitude = 'E11500'
    state.top = '500'
    state.comeFrom = 'OBS'
    state.observedTime = '100800'
    state.direction = 'W'
    state.speed = '20'
    state.intensityChange = 'NC'
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def ash(**fields):
    state = SigmetAshState('KMH')
    state.header = header()
    state.phenomenon = 'ASH'
    state.name = 'ASHVAL'
    state.currentLatitude = 'N1500'
    state.currentLongitude = 'E07348'
    state.flightLevelBase = '310'
    state.flightLevelTop = '450'
    state.comeFrom = 'OBS'
    state.observedTime = '100800'
    state.direction = 'ESE'
    state.speed = '65'
    state.intensityChange = 'NC'
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def cancel(**fields):
    state = SigmetCancelState()
    state.header = header()
    state.cancelSequence = '1'
    state.cancelBeginningTime = '100930'
    state.cancelEndingTime = '101430'
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def custom(**fields):
    state = SigmetCustomState()
    state.header = header()
    state.text = 'TS OBS'
    for name, value in fields.items():
        setattr(state, name, value)
    return state


class TestSigmetHeaderState:

    def test_compose_produces_the_first_line_with_a_trailing_dash(self):
        assert header().compose() == HEADER_LINE

    def test_a_complete_header_is_acceptable(self):
        assert header().isAcceptable() is True

    @pytest.mark.parametrize('field', HEADER_FIELDS)
    def test_any_blank_field_is_not_acceptable(self, field):
        assert header(**{field: ''}).isAcceptable() is False

    def test_clear_resets_every_field(self):
        state = header()
        state.clear()
        for field in HEADER_FIELDS:
            assert getattr(state, field) == ''


class TestBaseStateHelpers:

    def test_observation_wording_follows_come_from(self):
        state = BaseState('KMH')
        state.comeFrom = 'OBS'
        state.observedTime = '100800'
        assert state.observation() == 'OBS AT 100800Z'

        state.comeFrom = 'FCST'
        state.observedTime = '101000'
        assert state.observation() == 'FCST AT 101000Z'

    def test_an_observation_without_a_time_composes_nothing(self):
        state = BaseState('KMH')
        state.comeFrom = 'OBS'
        assert state.observation() == ''

    def test_a_forecast_without_a_time_degrades_to_the_come_from(self):
        state = BaseState('KMH')
        state.comeFrom = 'FCST'
        assert state.observation() == 'FCST'

    def test_stationary_wins_over_any_speed(self):
        state = BaseState('KMH')
        state.direction = 'STNR'
        state.speed = '25'
        assert state.movement() == 'STNR'

    def test_movement_without_a_speed_is_none(self):
        state = BaseState('KMH')
        state.direction = 'NE'
        assert state.movement() is None

    def test_movement_casts_the_speed_and_appends_the_unit(self):
        state = BaseState('KMH')
        state.direction = 'NE'
        state.speed = '25'
        assert state.movement() == 'MOV NE 25KMH'

    @pytest.mark.parametrize('base, top, expected', [
        ('80', '120', 'FL080/120'),
        ('80', '', 'FL080'),
        ('', '120', 'FL120'),
        ('', '', ''),
    ])
    def test_flight_level_without_a_format(self, base, top, expected):
        state = BaseState('KMH')
        state.flightLevelBase = base
        state.flightLevelTop = top
        assert state.flightLevel() == expected

    @pytest.mark.parametrize('format, expected', [
        ('TOP', 'TOP FL120'),
        ('TOP ABV', 'TOP ABV FL120'),
        ('BLW', 'BLW FL120'),
    ])
    def test_top_family_formats_use_the_top(self, format, expected):
        state = BaseState('KMH')
        state.flightLevelFormat = format
        state.flightLevelTop = '120'
        assert state.flightLevel() == expected

    def test_the_abv_format_uses_the_base(self):
        state = BaseState('KMH')
        state.flightLevelFormat = 'ABV'
        state.flightLevelBase = '80'
        assert state.flightLevel() == 'ABV FL080'

    def test_the_sfc_format_uses_the_top(self):
        state = BaseState('KMH')
        state.flightLevelFormat = 'SFC'
        state.flightLevelTop = '450'
        assert state.flightLevel() == 'SFC/FL450'


class TestSigmetGeneralState:

    def test_compose_message_interpolates_the_location_and_keeps_the_movement(self):
        message = general().composeMessage(FIR, {'location': 'N2000 E11000'})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA SEV TS OBS AT 100800Z N2000 E11000 FL080/120 MOV NE 25KMH NC=',
        ])

    def test_a_missing_location_key_drops_the_area_without_leaving_a_gap(self):
        # the graphic only reports finished sketches, so the key can be
        # absent; the message loses the area instead of crashing on it
        message = general().composeMessage(FIR, {})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA SEV TS OBS AT 100800Z FL080/120 MOV NE 25KMH NC=',
        ])

    def test_compose_message_in_forecast_mode_swaps_movement_for_the_forecast_tail(self):
        locations = {'location': 'N2000 E11000', 'forecastLocation': 'N2100 E11100'}
        message = general(hasForecast=True, forecastTime='101000').composeMessage(FIR, locations)
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA SEV TS OBS AT 100800Z N2000 E11000 FL080/120 NC FCST AT 101000Z N2100 E11100=',
        ])

    def test_a_complete_state_is_acceptable(self):
        assert general().isAcceptable() is True

    def test_a_state_without_a_hazard_is_not_acceptable(self):
        assert general(description='', phenomenon='').isAcceptable() is False

    def test_a_state_without_a_flight_level_is_not_acceptable(self):
        state = general(flightLevelBase='', flightLevelTop='', flightLevelFormat='')
        assert state.isAcceptable() is False

    def test_a_state_without_a_movement_is_not_acceptable(self):
        assert general(direction='', speed='').isAcceptable() is False

    def test_an_observation_needs_a_time(self):
        assert general(observedTime='').isAcceptable() is False

    def test_forecast_mode_accepts_an_empty_forecast_time(self):
        # CURRENT BEHAVIOR, pinned: forecast() renders 'FCST AT Z', which is
        # truthy, so forecastTime is effectively unchecked in this branch.
        # Revisit when composeMessage grows the locations argument.
        assert general(hasForecast=True, forecastTime='').isAcceptable() is True

    def test_clear_resets_its_fields_but_keeps_the_unit(self):
        state = general(hasForecast=True, forecastTime='101000')
        state.clear()
        assert state.description == ''
        assert state.phenomenon == ''
        assert state.observedTime == ''
        assert state.flightLevelTop == ''
        assert state.direction == ''
        assert state.hasForecast is False
        assert state.header.sequence == ''
        assert state.unit == 'KMH'


class TestSigmetTyphoonState:

    def test_flight_level_overrides_the_base_machinery(self):
        state = typhoon(flightLevelFormat='ABV', flightLevelBase='080')
        assert state.flightLevel() == 'TOP FL500'

    def test_compose_message_in_polygon_mode_interpolates_the_location(self):
        message = typhoon().composeMessage(FIR, {'location': 'N2000 E11000'})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA TC SALLY PSN N1800 E11500 CB OBS AT 100800Z N2000 E11000 TOP FL500 MOV W 20KMH NC=',
        ])

    def test_compose_message_in_circle_mode_describes_the_radius(self):
        message = typhoon(mode='circle', radius='200').composeMessage(FIR, {})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA TC SALLY PSN N1800 E11500 CB OBS AT 100800Z WI 200KM OF TC CENTRE TOP FL500 MOV W 20KMH NC=',
        ])

    def test_compose_message_branches_on_the_forecast_position_not_forecast_mode(self):
        # CURRENT BEHAVIOR, pinned: the forecast branch is chosen by the
        # presence of a forecast position, while hasForecast stays False and
        # isAcceptable still demands a movement -- the two disagree by design.
        state = typhoon(forecastTime='101000', forecastLatitude='N1740', forecastLongitude='E11430')
        assert state.forecastPosition() == 'FCST AT 101000Z TC CENTRE PSN N1740 E11430'
        message = state.composeMessage(FIR, {'location': 'N2000 E11000'})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA TC SALLY PSN N1800 E11500 CB OBS AT 100800Z N2000 E11000 TOP FL500 NC FCST AT 101000Z TC CENTRE PSN N1740 E11430=',
        ])

    def test_a_complete_state_is_acceptable(self):
        assert typhoon().isAcceptable() is True

    @pytest.mark.parametrize('field', ['phenomenon', 'name', 'currentLatitude', 'currentLongitude', 'top'])
    def test_a_missing_required_field_is_not_acceptable(self, field):
        assert typhoon(**{field: ''}).isAcceptable() is False

    def test_circle_mode_demands_a_radius(self):
        assert typhoon(mode='circle').isAcceptable() is False

    def test_forecast_mode_demands_the_forecast_position(self):
        # Unlike the general state, an empty forecastTime is rejected here.
        state = typhoon(hasForecast=True, forecastTime='')
        assert state.isAcceptable() is False

    def test_without_forecast_mode_a_missing_movement_is_rejected(self):
        state = typhoon(forecastTime='101000', forecastLatitude='N1740',
                        forecastLongitude='E11430', direction='', speed='')
        assert state.isAcceptable() is False

    def test_calc_forecast_position_needs_time_speed_and_direction(self):
        assert typhoon(forecastTime='').calcForecastPosition() is None
        assert typhoon(speed='').calcForecastPosition() is None
        assert typhoon(direction='STNR').calcForecastPosition() is None

    def test_calc_forecast_position_needs_a_time_basis(self):
        state = typhoon(forecastTime='101000', observedTime='',
                        header=header(beginningTime=''))
        assert state.calcForecastPosition() is None

    def test_calc_forecast_position_smoke(self):
        # the geometry itself belongs to the coordinate tests; here we only
        # pin that a complete state yields a position
        assert typhoon(forecastTime='101000').calcForecastPosition()

    def test_clear_resets_its_fields_and_the_mode(self):
        state = typhoon(mode='circle', radius='200', name='SALLY')
        state.clear()
        assert state.name == ''
        assert state.top == ''
        assert state.mode == 'polygon'
        assert state.header.sequence == ''
        assert state.unit == 'KMH'


class TestSigmetAshState:

    def test_an_eruption_composes_the_cld_position(self):
        message = ash().composeMessage(FIR, {'location': 'N2000 E11000'})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA VA ASH MT ASHVAL PSN N1500 E07348 VA CLD OBS AT 100800Z N2000 E11000 FL310/450 MOV ESE 65KMH NC=',
        ])

    def test_a_non_eruption_degrades_the_position_to_the_observation(self):
        message = ash(isEruption=False).composeMessage(FIR, {'location': 'N2000 E11000'})
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA VA ASH OBS AT 100800Z N2000 E11000 FL310/450 MOV ESE 65KMH NC=',
        ])

    def test_an_eruption_demands_the_volcano_position(self):
        assert ash(currentLatitude='', currentLongitude='').isAcceptable() is False

    def test_a_non_eruption_needs_no_coordinates(self):
        assert ash(isEruption=False, currentLatitude='', currentLongitude='').isAcceptable() is True

    def test_the_phenomenon_and_name_are_not_required(self):
        # CURRENT BEHAVIOR, pinned: the hazard always starts with the literal
        # 'VA', so it is never empty and isAcceptable never checks these two.
        assert ash(phenomenon='', name='').isAcceptable() is True

    def test_forecast_mode_demands_the_flight_level(self):
        assert ash(hasForecast=True, forecastTime='101000').isAcceptable() is True
        state = ash(hasForecast=True, forecastTime='101000',
                    flightLevelBase='', flightLevelTop='')
        assert state.isAcceptable() is False

    def test_clear_resets_its_fields_and_eruption_defaults_back_on(self):
        state = ash(isEruption=False, name='ASHVAL')
        state.clear()
        assert state.name == ''
        assert state.currentLatitude == ''
        assert state.isEruption is True
        assert state.header.sequence == ''
        assert state.unit == 'KMH'


class TestSigmetCancelState:

    def test_compose_message_cancels_by_sign_and_sequence(self):
        message = cancel().composeMessage(FIR)
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA CNL SIGMET 1 100930/101430=',
        ])

    def test_a_complete_state_is_acceptable(self):
        assert cancel().isAcceptable() is True

    @pytest.mark.parametrize('field', ['cancelSequence', 'cancelBeginningTime', 'cancelEndingTime'])
    def test_a_missing_cancel_field_is_not_acceptable(self, field):
        assert cancel(**{field: ''}).isAcceptable() is False

    def test_clear_resets_its_fields(self):
        state = cancel()
        state.clear()
        assert state.cancelSequence == ''
        assert state.cancelBeginningTime == ''
        assert state.cancelEndingTime == ''
        assert state.header.sequence == ''


class TestSigmetCustomState:

    def test_compose_message_joins_the_free_text(self):
        message = custom().composeMessage(FIR)
        assert message == '\n'.join([
            HEADER_LINE,
            'ZJSA TS OBS=',
        ])

    def test_an_empty_text_is_not_acceptable(self):
        assert custom(text='').isAcceptable() is False

    def test_a_filled_text_is_acceptable(self):
        assert custom().isAcceptable() is True

    def test_clear_resets_its_fields(self):
        state = custom()
        state.clear()
        assert state.text == ''
        assert state.header.sequence == ''
