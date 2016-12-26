import datetime

from PyQt5.QtCore import *
from models import Tafor, Schedule, Session


class AutoSendTAF(QObject):

    send = pyqtSignal()

    def run(self):
        db = Session()
        sch_queue = db.query(Schedule).filter_by(tafor_id=None).order_by(Schedule.schedule_time).all()
        now = datetime.datetime.utcnow()
        send_status = False

        for sch in sch_queue:
            #print(sch)

            if sch.schedule_time <= now:
                # print(sch)
                item = Tafor(tt=sch.tt, rpt=sch.rpt)
                db.add(item)
                db.flush()
                sch.tafor_id = item.id
                db.merge(sch)
                db.commit()

                send_status = True

        print(sch_queue)
        
        if send_status:
            self.send.emit()
            print('auto_send')
        else:
            print('nothing to do')



