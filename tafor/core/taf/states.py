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
        self.clouds = []  # e.g., ["FEW030", "SCT040"]
        self.cb = ""      # e.g., "BKN030CB"
        self.isCavok = False
        self.isNsc = False

    def composeWeather(self):
        if self.wind:
            winds = f"{self.wind}G{self.gust}{self.unit}" if self.gust else f"{self.wind}{self.unit}"
        else:
            winds = None

        allClouds = list(filter(None, self.clouds + ([self.cb] if self.cb else [])))
        sortedClouds = sorted(allClouds, key=lambda c: int(c[3:6]) if len(c) >= 6 and c[3:6].isdigit() else 0)

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
        self.cb = ""
        self.isCavok = False
        self.isNsc = False


class PrimaryState(SegmentState):
    def __init__(self, unit, icao="", spec="fc"):
        super().__init__(unit)
        self.icao = icao
        self.spec = spec
        self.date = ""
        self.period = ""
        self.durations = None  # (start, end) datetime tuple
        self.type = "NORMAL"  # NORMAL, AMD, COR, CNL
        self.sequence = ""
        self.temperatures = []  # List of TemperatureState

    def isAcceptable(self):
        if self.type == "CNL":
            return bool(self.icao and self.date and self.period and self.sequence)

        headerOk = bool(self.icao and self.date and self.period)

        hasWind = bool(self.wind)
        hasClouds = any([bool(c) for c in self.clouds] + [bool(self.cb)])
        weatherOk = hasWind and (self.isCavok or self.isNsc or (bool(self.visibility) and hasClouds))

        tempsOk = all(t.isAcceptable() for t in self.temperatures if t.value or t.time)

        sequenceOk = bool(self.sequence) if self.type in ["AMD", "COR"] else True

        return headerOk and weatherOk and sequenceOk and tempsOk

    def composeMessage(self):
        if self.type == "CNL":
            amd = "AMD"
            messages = ["TAF", amd, self.icao, self.date + "Z" if self.date else "", self.period, "CNL"]
            return " ".join(filter(None, messages))

        weatherPart = self.composeWeather()

        amd = "AMD" if self.type == "AMD" else ""
        cor = "COR" if self.type == "COR" else ""
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
        self.type = "NORMAL"
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
        oneRequired = any([self.isNsc, self.isCavok, self.wind, self.visibility, self.weather, self.weatherWithIntensity]
            + [bool(c) for c in self.clouds] + [bool(self.cb)])
        return bool(self.period) and oneRequired

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
        self.type = "BECMG"  # BECMG or TEMPO
        self.atChecked = False
        self.fmChecked = False
        self.tlChecked = False
        self.period = ""

    def isAcceptable(self):
        if self.isNosig:
            return True

        weatherOk = any([
            self.isNsc, self.isCavok, bool(self.wind), bool(self.visibility),
            bool(self.weather), bool(self.weatherWithIntensity),
            any(bool(c) for c in self.clouds), bool(self.cb)
        ])

        if any([self.atChecked, self.fmChecked, self.tlChecked]):
            return bool(self.period) and weatherOk

        return weatherOk

    def composeMessage(self):
        if self.isNosig:
            return "NOSIG"

        weatherPart = self.composeWeather()

        messages = [self.type]
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
