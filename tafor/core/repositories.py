import copy
import datetime

from sqlalchemy import and_

from tafor.core.models import Metar, Sigmet, Taf, Trend
from tafor.core.parsers.sigmet import SigmetParser
from tafor.core.taf import CurrentTaf
from tafor.core.utils.pagination import paginate


class SigmetFilter:

    def __init__(self, reportType=None, typeCode=None, includeCancelled=False):
        self.reportType = reportType
        self.typeCode = typeCode
        self.includeCancelled = includeCancelled

    def typeCodes(self):
        if self.typeCode:
            return [self.typeCode]

        if self.reportType == 'SIGMET':
            return ['WS', 'WC', 'WV']

        if self.reportType == 'AIRMET':
            return ['WA']

        return []


class Repository(object):

    def __init__(self, database):
        self.database = database

    def queryset(self, session, model, reportType=None, date=None, keywords=None):
        query = session.query(model).order_by(model.created.desc())

        if reportType == 'SIGMET':
            query = query.filter(model.type != 'WA')

        if reportType == 'AIRMET':
            query = query.filter(model.type == 'WA')

        if date:
            delta = datetime.timedelta(days=1)
            query = query.filter(and_(model.created >= date, model.created < date + delta))

        if keywords:
            words = [model.text.like('%' + word + '%') for word in keywords]
            query = query.filter(and_(*words))

        return query

    def paginated(self, model, reportType=None, date=None, keywords=None, page=1, perPage=12):
        with self.database.session() as session:
            queryset = self.queryset(session, model, reportType=reportType, date=date, keywords=keywords)
            return paginate(queryset, page, perPage=perPage)

    def filtered(self, model, reportType=None, start=None, end=None):
        with self.database.session() as session:
            query = session.query(model)

            if reportType == 'SIGMET':
                query = query.filter(model.type != 'WA')

            if reportType == 'AIRMET':
                query = query.filter(model.type == 'WA')

            query = query.filter(
                model.created >= start, model.created < end + datetime.timedelta(hours=24)).order_by(model.created.desc())

            return query.all()


class TafRepository(Repository):

    def available(self, type, message):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=32)
        with self.database.session() as session:
            tafs = session.query(Taf).filter(type == type, Taf.created > recent).all()

        def _match(objects, message):
            for taf in objects:
                if taf.flatternedText() == message:
                    return taf

        matched = _match(tafs, message)
        if matched:
            if not matched.confirmed:
                matched.confirmed = datetime.datetime.utcnow()
                return matched
        else:
            return Taf(type=type, text=message, source='api', confirmed=datetime.datetime.utcnow())

    def hasRecent(self, period, hours=32):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        with self.database.session() as session:
            return session.query(Taf).filter(
                Taf.text.contains(period), Taf.created > recent).first()

    def amendCount(self, period, kind):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        with self.database.session() as session:
            query = session.query(Taf).filter(Taf.text.contains(period), Taf.created > recent)
            return query.filter(Taf.text.contains(kind)).count()

    def latest(self, type):
        with self.database.session() as session:
            return session.query(Taf).filter_by(type=type).order_by(Taf.created.desc()).first()

    def status(self, spec, delayMinutes=None):
        currentTaf = CurrentTaf(spec)
        period = currentTaf.period(strict=False)

        shouldRemind = currentTaf.isExpired(offset=5)
        isExpired = False

        # Ignore AMD COR message
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=32)

        with self.database.session() as session:
            recent = session.query(Taf).filter(Taf.text.contains(period),  ~Taf.text.contains('AMD'),
            ~Taf.text.contains('COR'), Taf.created > expired).order_by(Taf.created.desc()).first()

        if currentTaf.isExpired(offset=delayMinutes):
            if recent:
                if not recent.confirmed:
                    isExpired = True
            else:
                isExpired = True

        # The alarm clock no longer rings after the cancel message is issued
        latest = self.latest(currentTaf.spec.type)
        if latest and latest.isCnl():
            isExpired = False
            shouldRemind = False

        return {
                'period': period,
                'message': recent,
                'isExpired': isExpired,
                'shouldRemind': shouldRemind,
            }


class MetarRepository(Repository):

    def available(self, type, message):
        with self.database.session() as session:
            last = session.query(Metar).filter_by(type=type).order_by(Metar.created.desc()).first()

        if last is None or last.text != message:
            return Metar(type=type, text=message)

    def latest(self, hours=2):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        with self.database.session() as session:
            return session.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).first()

    def range(self, start, end):
        with self.database.session() as session:
            return session.query(Metar).filter(
                Metar.created >= start, Metar.created < end).order_by(Metar.created.asc()).all()


class SigmetRepository(Repository):

    def countToday(self, type):
        time = datetime.datetime.utcnow()
        begin = datetime.datetime(time.year, time.month, time.day)

        with self.database.session() as session:
            query = session.query(Sigmet).filter(Sigmet.created > begin)

            if type == 'WA':
                query = query.filter(Sigmet.type == 'WA')
            else:
                query = query.filter(Sigmet.type != 'WA')

            return query.all()

    def latest(self, type, excludeCnl=True):
        with self.database.session() as session:
            query = session.query(Sigmet).filter(Sigmet.type == type)

            if excludeCnl:
                query = query.filter(~Sigmet.text.contains('CNL'))

            return query.order_by(Sigmet.created.desc()).first()

    def current(self, hours=24):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        with self.database.session() as session:
            records = session.query(Sigmet).filter(Sigmet.created > recent).order_by(Sigmet.created.asc()).all()

        sigmets = []
        cancels = []
        for sig in records:
            if not sig.isExpired():
                if sig.isCnl():
                    cancels.append(sig)
                else:
                    sigmets.append(sig)

        currents = []
        cancelSequences = [s.parser().cancelSequence() for s in cancels]
        for sig in sigmets:
            parser = sig.parser()
            sequence = parser.sequence(), parser.validTime()
            if sequence not in cancelSequences:
                currents.append(sig)

        cnls = copy.copy(cancels)
        sequences = [(s.parser().sequence(), s.parser().validTime()) for s in sigmets]
        for cnl in cancels:
            if cnl.parser().cancelSequence() in sequences:
                cnls.remove(cnl)

        currents = currents + cnls
        currents.sort(key=lambda x: x.created)

        return currents

    def available(self, type, messages):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        time = datetime.datetime.utcnow()

        with self.database.session() as session:
            sigmets = session.query(Sigmet).filter(Sigmet.created > recent).all()

        availables = []
        for message in messages:
            message = ' '.join(message.split())
            parser = SigmetParser(message)

            if parser not in [sig.parser() for sig in sigmets]:
                item = Sigmet(type=type, heading=parser.heading, text=parser.text + '=', source='api', confirmed=time)
                availables.append(item)

            for sig in sigmets:
                if not sig.confirmed and sig.parser() == parser:
                    sig.confirmed = time
                    availables.append(sig)

        return availables


class MessageRepository(Repository):

    def __init__(self, database):
        super().__init__(database)
        self.metar = MetarRepository(database)
        self.taf = TafRepository(database)
        self.sigmet = SigmetRepository(database)

    def available(self, messages, wishlist=None):
        availables = []
        for key, text in messages.items():
            if wishlist and key not in wishlist:
                continue

            if key in ['SA', 'SP']:
                message = self.metar.available(key, text)
                if message:
                    availables.append(message)

            if key in ['FC', 'FT']:
                message = self.taf.available(key, text)
                if message:
                    availables.append(message)

            if key in ['WS', 'WC', 'WV', 'WA']:
                message = self.sigmet.available(key, text)
                if message:
                    availables += message

        return availables

    def recent(self, spec, since, includeSigmet=False, currentSigmets=None):
        with self.database.session() as session:
            taf = session.query(Taf).filter(Taf.created > since, Taf.type == spec).order_by(Taf.created.desc()).first()
            trend = session.query(Trend).order_by(Trend.created.desc()).first()
            metar = session.query(Metar).filter(Metar.created > since).order_by(Metar.created.desc()).first()

        if trend and trend.isNosig():
            trend = None

        sigmets = currentSigmets if includeSigmet and currentSigmets else []

        return {
            'taf': taf,
            'trend': trend,
            'metar': metar,
            'sigmets': sigmets,
        }

    def add(self, message):
        with self.database.session() as session:
            session.add(message)
