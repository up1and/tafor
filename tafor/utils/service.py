import copy
import datetime

from tafor import logger
from tafor.models import db, Metar, Sigmet


def latestMetar():
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    queryset = db.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc())
    return queryset.first()

def currentSigmet(type=None, order='desc', showUnmatched=False):
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    queryset = db.query(Sigmet).filter(Sigmet.sent > recent).order_by(Sigmet.sent.desc())

    if type:
        queryset = queryset.filter(Sigmet.type == type)

    sigmets = []
    cancels = []
    for sig in queryset.all():
        if not sig.isExpired():
            if sig.isCnl():
                cancels.append(sig)
            else:
                sigmets.append(sig)

    currents = []
    cancelSequences = [s.parser().cancelSequence() for s in cancels]
    for sig in sigmets:
        parser = sig.parser()
        sequence = parser.sequence(), '/'.join(parser.valids())
        if sequence not in cancelSequences:
            currents.append(sig)

    if showUnmatched:
        cnls = copy.copy(cancels)
        sequences = [(s.parser().sequence(), '/'.join(s.parser().valids())) for s in sigmets]
        for cnl in cancels:
            if cnl.parser().cancelSequence() in sequences:
                cnls.remove(cnl)

        currents = currents + cnls
        currents.sort(key=lambda x: x.sent, reverse=True)

    if order == 'asc':
        currents.reverse()

    return currents
