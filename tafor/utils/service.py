import copy
import datetime

from tafor.models import db, Sigmet


def currentSigmet(tt=None, order='desc', hasCnl=False):
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=8)
    queryset = db.query(Sigmet).filter(Sigmet.sent > recent).order_by(Sigmet.sent.desc())

    if tt:
        queryset = queryset.filter(Sigmet.tt == tt)

    if order == 'asc':
        queryset = queryset.order_by(Sigmet.sent.asc())

    sigmets = []
    cancels = []
    for sig in queryset.all():
        if not sig.isExpired():
            if sig.isCnl():
                cancels.append(sig)
            else:
                sigmets.append(sig)

    currents = []
    cancelSequences = [s.cancelSequence for s in cancels]
    for sig in sigmets:
        if sig.sequence not in cancelSequences:
            currents.append(sig)

    if hasCnl:
        cnls = copy.copy(cancels)
        sequences = [s.sequence for s in sigmets]
        for cnl in cancels:
            if cnl.cancelSequence in sequences:
                cnls.remove(cnl)
                
        currents = currents + cnls

    return currents
