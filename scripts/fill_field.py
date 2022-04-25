import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tafor.models import db, Taf, Trend, Sigmet, Other


def addProtocol(model):
    items = db.query(model).filter(model.protocol == None).all()
    for item in items:
        if item.raw:
            item.protocol = 'aftn'
            db.add(item)

    db.commit()

def addSource(model):
    items = db.query(model).filter(model.source == None).all()
    for item in items:
        if item.raw:
            item.source = 'self'
        else:
            item.source = 'api'
        
        db.add(item)

    db.commit()

def main():
    for model in [Taf, Trend, Sigmet, Other]:
        addProtocol(model)
        addSource(model)
    

if __name__ == '__main__':
    main()