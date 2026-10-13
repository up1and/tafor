import datetime
import logging

from sqlalchemy import and_

from tafor.core.models import Metar, Sigmet, Taf, Trend
from tafor.core.parsers.sigmet import SigmetParser
from tafor.core.taf import CurrentTaf
from tafor.core.utils.pagination import paginate
from tafor.core.utils.time import utcnow


logger = logging.getLogger('tafor.repositories')


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

    def reconcile(self, session, type, message, now):
        """Find how an incoming TAF stands against the stored ones.

        Returns the stored report that the feed has now acknowledged and that
        still needs its ``confirmed`` stamp, a fresh unsaved Taf when the
        report has not been stored, or None when it was already confirmed.
        Nothing is written here: deciding and writing are split so that
        ``save()`` stays the only writer on the ingest path.
        """
        recent = now - datetime.timedelta(hours=32)
        tafs = session.query(Taf).filter(Taf.type == type, Taf.created > recent).all()

        for taf in tafs:
            if taf.flattenedText() != message:
                continue

            if taf.confirmed:
                return

            return taf

        return Taf(type=type, text=message, source='api', confirmed=now)

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

    def reconcile(self, session, type, message, now):
        """Return a fresh Metar when the feed has delivered an observation the
        latest stored one does not already carry, or None when it repeats it.

        An observation is never confirmed, so this only ever answers 'new' or
        'skip'; it returns nothing to stamp.
        """
        last = session.query(Metar).filter_by(type=type).order_by(Metar.created.desc()).first()

        if last is not None and last.text == message:
            return

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

    def reconcile(self, session, type, messages, now):
        """Find how an incoming SIGMET batch stands against the stored ones.

        Returns the stored reports the feed has now acknowledged and that
        still need their ``confirmed`` stamp, plus a fresh unsaved Sigmet for
        every report not stored yet. Nothing is written here: deciding and
        writing are split so that ``save()`` stays the only writer on the
        ingest path.

        The stored parsers are built once for the whole batch, since parsing
        is the expensive half of the comparison.
        """
        recent = now - datetime.timedelta(hours=24)
        sigmets = session.query(Sigmet).filter(Sigmet.created > recent).all()
        stored = [(sig, sig.parser()) for sig in sigmets]

        results = []
        for message in messages:
            message = ' '.join(message.split())
            parser = SigmetParser(message)

            matched = [sig for sig, cached in stored if cached == parser]
            if matched:
                for sig in matched:
                    # A report already claimed by an earlier message in this
                    # batch is not claimed twice, and a confirmed one is done.
                    if not sig.confirmed and sig not in results:
                        results.append(sig)
                continue

            item = Sigmet(type=type, heading=parser.heading, text=parser.text + '=', source='api', confirmed=now)
            results.append(item)
            # Keep the batch's own additions visible, so a payload that
            # repeats the same report does not store it twice.
            stored.append((item, parser))

        return results


class MessageRepository(Repository):

    def __init__(self, database):
        super().__init__(database)
        self.metar = MetarRepository(database)
        self.taf = TafRepository(database)
        self.sigmet = SigmetRepository(database)

    def save(self, messages, types=None):
        """Take the fetched payload, match it against what is stored, and
        write the outcome in one transaction.

        Returns the messages the feed added or confirmed, in payload order.
        The log lines are emitted after the commit, so a batch that rolls
        back leaves no record of a message that was never stored.
        """
        now = utcnow()
        staged = []

        with self.database.session() as session:
            for key, value in messages.items():
                if types and key not in types:
                    continue

                results = []
                if key in ['SA', 'SP']:
                    message = self.metar.reconcile(session, key, value, now)
                    if message:
                        results.append(message)

                if key in ['FC', 'FT']:
                    message = self.taf.reconcile(session, key, value, now)
                    if message:
                        results.append(message)

                if key in ['WS', 'WC', 'WV', 'WA']:
                    results += self.sigmet.reconcile(session, key, value, now)

                for message in results:
                    if message.id is None:
                        session.add(message)
                        staged.append((message, 'Save'))
                    else:
                        message.confirmed = now
                        staged.append((message, 'Confirm'))

        for message, label in staged:
            logger.info('%s %s %s', label, message.type, message.text)

        return [message for message, _ in staged]

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
