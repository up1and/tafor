import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from uuid import uuid4

from tafor.models import db, Taf, Trend, Sigmet, Other


def addProtocol(model):
    with db.session() as session:
        items = session.query(model).filter(model.protocol == None).all()
        for item in items:
            if item.raw:
                item.protocol = 'aftn'
                session.add(item)

def addSource(model):
    with db.session() as session:
        items = session.query(model).filter(model.source == None).all()
        for item in items:
            if item.raw:
                item.source = 'self'
            else:
                item.source = 'api'
            
            session.add(item)

def addUuid(model):
    with db.session() as session:
        items = session.query(model).filter(model.uuid == None).all()
        for item in items:
            item.uuid = str(uuid4())
            
            session.add(item)

def main():
    for model in [Taf, Trend, Sigmet, Other]:
        addProtocol(model)
        addSource(model)
        addUuid(model)
    

if __name__ == '__main__':
    main()
