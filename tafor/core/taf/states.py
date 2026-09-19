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
        self.durations = None  # (start, end) datetime tuple
        self.modifier = None  # None (normal report), 'AMD', 'COR' or 'CNL'
        self.sequence = ""
        self.temperatures = []  # List of TemperatureState

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


class TrendState(SegmentState):

    def __init__(self, unit):
        super().__init__(unit)
        self.isNosig = False
        self.indicator = "BECMG"  # BECMG or TEMPO, as in GroupState
        self.atChecked = False
        self.fmChecked = False
        self.tlChecked = False
        self.period = ""

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
