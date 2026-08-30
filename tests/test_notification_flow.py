from tafor.core.config import createConfig
from tafor.core.states import createContext
from tests.mocks import MockConfig


def test_notification_changed_emits_lowercase_type():
    conf = createConfig(settings=MockConfig())
    context = createContext(conf)
    received = []
    context.event.notificationChanged.connect(received.append)

    context.notification.metar.setState({'message': 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030=', 'validation': True})
    assert received[-1] == 'metar'

    context.notification.sigmet.setState({'message': 'SIGMET YUSO 300400Z ...'})
    assert received[-1] == 'sigmet'

    context.notification.metar.clear()
    assert received[-1] == 'unknown'
