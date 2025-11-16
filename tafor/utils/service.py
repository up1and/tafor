import copy
import datetime

from tafor.models import db, Metar, Sigmet


def latestMetar():
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    with db.session() as session:
        metar = session.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).first()
        return metar

def currentSigmet():
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    with db.session() as session:
        records = session.query(Sigmet).filter(Sigmet.created > recent).order_by(Sigmet.created.asc()).all()

    sigmets = []
    cancels = []
    for sig in records:
        if not sig.isExpired():
            if sig.isCnl():
                cancels.append(sig)
            else:
                sigmets.append(sig)

    # add valid sigmets, not cancelled
    currents = []
    cancelSequences = [s.parser().cancelSequence() for s in cancels]
    for sig in sigmets:
        parser = sig.parser()
        sequence = parser.sequence(), parser.validTime()
        if sequence not in cancelSequences:
            currents.append(sig)

    # add cancel sigmet that not match any current sigmet
    cnls = copy.copy(cancels)
    sequences = [(s.parser().sequence(), s.parser().validTime()) for s in sigmets]
    for cnl in cancels:
        if cnl.parser().cancelSequence() in sequences:
            cnls.remove(cnl)

    currents = currents + cnls
    currents.sort(key=lambda x: x.created)

    return currents
