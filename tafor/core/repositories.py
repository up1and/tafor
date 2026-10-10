import datetime

from sqlalchemy import and_

from tafor.core.models import Metar, Sigmet, Taf, Trend
from tafor.core.parsers.sigmet import SigmetParser
from tafor.core.taf import CurrentTaf
from tafor.core.utils.pagination import paginate
from tafor.core.utils.time import utcnow


def subscribedTypes(tafSpec, sigmetEnabled):
    """Telegram types the app subscribes to, derived from the enabled products."""
    types = ['SA', 'SP', 'FT' if tafSpec else 'FC']
    if sigmetEnabled:
        types.extend(['WS', 'WC', 'WV', 'WA'])
    return types


class SigmetFilter:

    def __init__(self, category=None, designator=None, includeCancelled=False):
        self.category = category
        self.designator = designator
        self.includeCancelled = includeCancelled

    def designators(self):
        if self.designator:
            return [self.designator]

        if self.category == 'SIGMET':
            return ['WS', 'WC', 'WV']

        if self.category == 'AIRMET':
            return ['WA']

        return []


class Repository:

    def __init__(self, database):
        self.database = database

    def queryset(self, session, model, category=None, date=None, keywords=None):
        query = session.query(model).order_by(model.created.desc())

        if category == 'SIGMET':
            query = query.filter(model.type != 'WA')

        if category == 'AIRMET':
            query = query.filter(model.type == 'WA')

        if date:
            delta = datetime.timedelta(days=1)
            query = query.filter(and_(model.created >= date, model.created < date + delta))

        if keywords:
            words = [model.text.like('%' + word + '%') for word in keywords]
            query = query.filter(and_(*words))

        return query

    def paginated(self, model, category=None, date=None, keywords=None, page=1, perPage=12, total=None):
        with self.database.session() as session:
            queryset = self.queryset(session, model, category=category, date=date, keywords=keywords)
            return paginate(queryset, page, perPage=perPage, total=total)

    def filtered(self, model, category=None, start=None, end=None):
        with self.database.session() as session:
            query = session.query(model)

            if category == 'SIGMET':
                query = query.filter(model.type != 'WA')

            if category == 'AIRMET':
                query = query.filter(model.type == 'WA')

            query = query.filter(
                model.created >= start, model.created < end + datetime.timedelta(hours=24)).order_by(model.created.desc())

            return query.all()


class TafRepository(Repository):

    def available(self, type, message):
        recent = utcnow() - datetime.timedelta(hours=32)
        with self.database.session() as session:
            tafs = session.query(Taf).filter(Taf.type == type, Taf.created > recent).all()

        def _match(objects, message):
            for taf in objects:
                if taf.flattenedText() == message:
                    return taf

        matched = _match(tafs, message)
        if matched:
            if not matched.confirmed:
                matched.confirmed = utcnow()
                return matched
        else:
            return Taf(type=type, text=message, source='api', confirmed=utcnow())

    def hasRecent(self, period, hours=32):
        recent = utcnow() - datetime.timedelta(hours=hours)
        with self.database.session() as session:
            return session.query(Taf).filter(
                Taf.text.contains(period), Taf.created > recent).first()

    def amendCount(self, period, modifier):
        """How many messages with this marker have already been sent for this
        period. The notation built from the count lives in core/taf/compose.py."""
        recent = utcnow() - datetime.timedelta(hours=24)
        with self.database.session() as session:
            query = session.query(Taf).filter(Taf.text.contains(period), Taf.created > recent)
            return query.filter(Taf.text.contains(modifier)).count()

    def latest(self, type):
        with self.database.session() as session:
            return session.query(Taf).filter_by(type=type).order_by(Taf.created.desc()).first()

    def status(self, spec, delayMinutes=None):
        currentTaf = CurrentTaf(spec)
        period = currentTaf.period()

        shouldRemind = currentTaf.isExpired(minutes=5)
        isExpired = False

        # Ignore AMD COR message
        expired = utcnow() - datetime.timedelta(hours=32)

        with self.database.session() as session:
            recent = session.query(Taf).filter(Taf.text.contains(period),  ~Taf.text.contains('AMD'),
            ~Taf.text.contains('COR'), Taf.created > expired).order_by(Taf.created.desc()).first()

        if currentTaf.isExpired(minutes=delayMinutes):
            if recent:
                if not recent.confirmed:
                    isExpired = True
            else:
                isExpired = True

        # The alarm clock no longer rings after the cancel message is issued
        latest = self.latest(currentTaf.spec.designator)
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
        recent = utcnow() - datetime.timedelta(hours=hours)
        with self.database.session() as session:
            return session.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).first()

    def range(self, start, end):
        with self.database.session() as session:
            return session.query(Metar).filter(
                Metar.created >= start, Metar.created < end).order_by(Metar.created.asc()).all()


class SigmetRepository(Repository):

    def countToday(self, type):
        time = utcnow()
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
        """The SIGMETs still in force: the ones never cancelled, plus the
        cancellations that cancel nothing (a CNL can arrive before the report
        it cancels, and the operator still needs to see it).

        A report and the cancellation that targets it annihilate each other --
        the report leaves ``current`` and the cancellation is not listed on its
        own. Both directions are the same test on the same pair of keys, so it
        is done once: collect the key of every report and the target of every
        cancellation, then keep a record only when the other set does not
        claim it.
        """
        recent = utcnow() - datetime.timedelta(hours=hours)
        with self.database.session() as session:
            records = session.query(Sigmet).filter(Sigmet.created > recent).order_by(Sigmet.created.asc()).all()

        entries = []
        for sig in records:
            if sig.isExpired():
                continue

            parser = sig.parser()
            isCnl = sig.isCnl()
            # A report is addressed by its own sequence and validity; a
            # cancellation by the pair it names. They are compared as one key.
            key = parser.cancelSequence() if isCnl else (parser.sequence(), parser.validTime())
            entries.append((sig, isCnl, key))

        cancelledKeys = {key for _, isCnl, key in entries if isCnl}
        reportKeys = {key for _, isCnl, key in entries if not isCnl}

        currents = []
        cancels = []
        for sig, isCnl, key in entries:
            if isCnl:
                if key not in reportKeys:
                    cancels.append(sig)
            elif key not in cancelledKeys:
                currents.append(sig)

        return sorted(currents + cancels, key=lambda x: x.created)

    def available(self, type, messages):
        recent = utcnow() - datetime.timedelta(hours=24)
        time = utcnow()

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

    def available(self, messages, types=None):
        availables = []
        for key, text in messages.items():
            if types and key not in types:
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


class Repositories:
    """Every repository over one database, built once at the assembly
    point and shared by the services and widgets that query them."""

    def __init__(self, database):
        self.taf = TafRepository(database)
        self.metar = MetarRepository(database)
        self.sigmet = SigmetRepository(database)
        self.message = MessageRepository(database)
