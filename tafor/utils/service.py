import copy
import datetime

from tafor import logger
from tafor.models import db, Taf, Sigmet, Task
from tafor.utils.message import AFTNMessageGenerator
from tafor.utils.thread import SerialThread


def currentSigmet(tt=None, order='desc', showUnmatched=False):
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=8)
    queryset = db.query(Sigmet).filter(Sigmet.sent > recent).order_by(Sigmet.sent.desc())

    if tt:
        queryset = queryset.filter(Sigmet.tt == tt)

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


class DelaySend(object):

    def __init__(self, callback=None):
        self.task = None
        self.item = None
        self.aftn = None
        self.callback = callback

        now = datetime.datetime.utcnow()
        tasks = db.query(Task).filter(Task.taf_id==None, Task.planning<=now).all()
        if tasks:
            self.task = min(tasks, key=lambda x: x.planning)

    def start(self):
        if not self.task:
            return

        message = '\n'.join([self.task.sign, self.task.rpt])
        self.aftn = AFTNMessageGenerator(message, time=self.task.planning)

        self.thread = SerialThread(self.aftn.toString())
        self.thread.doneSignal.connect(self.commit)
        self.thread.start()

    def commit(self, error):
        if error:
            self.callback(self.task.rpt, error)
            return

        self.item = Taf(tt=self.task.tt, sign=self.task.sign, rpt=self.task.rpt, raw=self.aftn.toJson())
        db.add(self.item)
        db.flush()
        self.task.taf_id = self.item.id
        db.merge(self.task)
        db.commit()

        self.callback(self.task.rpt)
        logger.info('Task {} has been sent'.format(self.item.rpt))
