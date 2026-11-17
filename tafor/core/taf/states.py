from tafor.core.taf.spec import SpecFC


class TemperatureState:

    def __init__(self, mode="max"):
        self.mode = mode
        self.value = ""
        self.time = ""

    def isAcceptable(self):
        return bool(self.value and self.time)

    def composeMessage(self):
        if not self.isAcceptable():
            return ""
        prefix = "TX" if self.mode == "max" else "TN"
        return f"{prefix}{self.value}/{self.time}Z"

    def clear(self):
        self.value = ""
        self.time = ""


class SegmentState:

    def __init__(self, unit):
        self.unit = unit
        self.wind = ""
        self.gust = ""
        self.visibility = ""
        self.weather = ""
        self.weatherWithIntensity = ""
        # Every layer, the CB one included. A CB layer is an independent
        # phenomena layer, marked by its 'CB' suffix: ["FEW030", "BKN040CB"]
        self.clouds = []
        self.isCavok = False
        self.isNsc = False

    def composeWeather(self):
        if self.wind:
            winds = f"{self.wind}G{self.gust}{self.unit}" if self.gust else f"{self.wind}{self.unit}"
        else:
            winds = None

        sortedClouds = sorted(self.clouds, key=lambda c: int(c[3:6]) if len(c) >= 6 and c[3:6].isdigit() else 0)

        if self.isCavok:
            elements = [winds, "CAVOK"]
        elif self.isNsc:
            if any([self.weather, self.weatherWithIntensity]) or (self.visibility and self.visibility != '9999'):
                elements = [winds, self.visibility, self.weatherWithIntensity, self.weather, "NSC"]
            else:
                elements = [winds, "CAVOK"]
        else:
            elements = [winds, self.visibility, self.weatherWithIntensity, self.weather] + sortedClouds

        return " ".join(filter(None, elements))

    def clear(self):
        self.wind = ""
        self.gust = ""
        self.visibility = ""
        self.weather = ""
        self.weatherWithIntensity = ""
        self.clouds = []
        self.isCavok = False
        self.isNsc = False


class PrimaryState(SegmentState):

    def __init__(self, unit, icao="", spec=SpecFC):
        super().__init__(unit)
        self.icao = icao
        self.spec = spec
        self.date = ""
        self.period = ""
        self.durations = None  # (start, end) datetime tuple, derived from period
        self.modifier = None  # None (normal report), 'AMD', 'COR' or 'CNL'
        self.sequence = ""
        self.temperatures = []  # List of TemperatureState, in reporting order

    def addTemperature(self, state):
        """Register a temperature group's state.

        A group registers itself as it is built, so the message composes from
        this list without the primary report knowing how many groups there are
        or what they look like.
        """
        self.temperatures.append(state)

    def isAcceptable(self):
        if self.modifier == "CNL":
            return bool(self.icao and self.date and self.period and self.sequence)

        headerOk = bool(self.icao and self.date and self.period)

        hasWind = bool(self.wind)
        hasClouds = bool(self.clouds)
        weatherOk = hasWind and (self.isCavok or self.isNsc or (bool(self.visibility) and hasClouds))

        tempsOk = all(t.isAcceptable() for t in self.temperatures)

        sequenceOk = bool(self.sequence) if self.modifier in ("AMD", "COR") else True

        return headerOk and weatherOk and sequenceOk and tempsOk

    def composeMessage(self):
        if self.modifier == "CNL":
            amd = "AMD"
            messages = ["TAF", amd, self.icao, self.date + "Z" if self.date else "", self.period, "CNL"]
            return " ".join(filter(None, messages))

        weatherPart = self.composeWeather()

        amd = "AMD" if self.modifier == "AMD" else ""
        cor = "COR" if self.modifier == "COR" else ""
        timez = self.date + "Z" if self.date else ""

        validTemps = [t for t in self.temperatures if t.isAcceptable()]
        sortedTemps = sorted(validTemps, key=lambda t: (0 if t.mode == "max" else 1, t.time))
        tempTexts = [t.composeMessage() for t in sortedTemps]

        messages = ["TAF", amd, cor, self.icao, timez, self.period, weatherPart] + tempTexts
        return " ".join(filter(None, messages))

    def clear(self):
        super().clear()
        self.date = ""
        self.period = ""
        self.durations = None
        self.modifier = None
        self.sequence = ""
        for t in self.temperatures:
            t.clear()


class GroupState(SegmentState):

    def __init__(self, unit, indicator="TEMPO"):
        super().__init__(unit)
        self.indicator = indicator  # FM, BECMG, TEMPO
        self.period = ""
        self.durations = None  # (start, end) datetime tuple

    def isAcceptable(self):
        return bool(self.period) and bool(self.composeWeather())

    def composeMessage(self):
        weatherPart = self.composeWeather()

        if self.indicator == "FM":
            return f"FM{self.period} {weatherPart}".strip()
        else:
            return f"{self.indicator} {self.period} {weatherPart}".strip()

    def clear(self):
        super().clear()
        self.period = ""
        # A derived window outliving the period it came from is a stale value
        # nobody can see; the primary resets its own, so this one does too.
        self.durations = None


class TrendState(SegmentState):

    def __init__(self, unit):
        super().__init__(unit)
        self.isNosig = False
        self.indicator = "BECMG"  # BECMG or TEMPO, as in GroupState
        self.atChecked = False
        self.fmChecked = False
        self.tlChecked = False
        self.period = ""

    @classmethod
    def fromTokens(cls, tokens, unit, intensityWeather):
        """Read a parsed trend group's tokens into a state.

        The token vocabulary is the parser's and the state is the editor's;
        this is the one place a message becomes form state, so a load goes
        through here and populate() instead of through the widgets.

        ``intensityWeather`` is the configured phenomena that belong in the
        intensity box; the box is the one whose validator will keep them.
        """
        state = cls(unit)
        state.isNosig = 'nosig' in tokens

        if 'sign' in tokens:
            state.indicator = 'BECMG' if tokens['sign']['text'] == 'BECMG' else 'TEMPO'

        if 'fmtl' in tokens:
            groups = tokens['fmtl']['text'].split()
            if len(groups) == 2:
                state.fmChecked = state.tlChecked = True
                state.period = '{}/{}'.format(groups[0][2:], groups[1][2:])
            else:
                prefix, period = groups[0][:2], groups[0][2:]
                state.atChecked = prefix == 'AT'
                state.fmChecked = prefix == 'FM'
                state.tlChecked = prefix == 'TL'
                state.period = period

        if 'wind' in tokens:
            # The widget holds the digits; the unit comes from the settings.
            wind = tokens['wind']['text'].replace('MPS', '').replace('KT', '')
            if 'G' in wind:
                state.wind, state.gust = wind.split('G')
            else:
                state.wind = wind

        if 'vis' in tokens:
            state.visibility = tokens['vis']['text']

        if 'weather' in tokens:
            # Which box a phenomenon belongs in is the settings' call, not
            # the sign's: only the box that lists it will keep it on the
            # next collect(). One phenomenon per box, so a later group
            # replaces an earlier one.
            for weather in tokens['weather']['text'].split():
                if weather.lstrip('+-') in intensityWeather:
                    state.weatherWithIntensity = weather
                else:
                    state.weather = weather

        if 'cloud' in tokens:
            clouds = tokens['cloud']['text'].split()
            state.isNsc = 'NSC' in clouds
            # The CB layer is a `clouds` entry marked by its suffix; TCU
            # stays a layer, because the CB box re-suffixes with 'CB'. SKC
            # stays one too: only NSC has a box of its own.
            state.clouds = [cloud for cloud in clouds
                            if cloud != 'NSC' and not cloud.endswith('CB')]
            cb = next((cloud for cloud in clouds if cloud.endswith('CB')), None)
            if cb:
                state.clouds.append(cb)

        state.isCavok = 'cavok' in tokens
        return state

    def isAcceptable(self):
        if self.isNosig:
            return True

        weatherOk = bool(self.composeWeather())

        if any([self.atChecked, self.fmChecked, self.tlChecked]):
            return bool(self.period) and weatherOk

        return weatherOk

    def composeMessage(self):
        if self.isNosig:
            return "NOSIG"

        weatherPart = self.composeWeather()

        messages = [self.indicator]
        if self.atChecked or self.fmChecked or self.tlChecked:
            if self.fmChecked and self.tlChecked:
                parts = self.period.split('/')
                if len(parts) == 2:
                    messages.append(f"FM{parts[0]} TL{parts[1]}")
            else:
                prefix = ""
                if self.atChecked: prefix = "AT"
                elif self.fmChecked: prefix = "FM"
                elif self.tlChecked: prefix = "TL"
                messages.append(f"{prefix}{self.period}")

        messages.append(weatherPart)
        return " ".join(filter(None, messages))

    def clear(self):
        super().clear()
        self.isNosig = False
        self.atChecked = False
        self.fmChecked = False
        self.tlChecked = False
        self.period = ""
