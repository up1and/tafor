import logging

import requests

from tafor.core.utils.common import appInfo

logger = logging.getLogger('tafor.client')


def headers():
    return {'User-Agent': 'Tafor/{version}+{revision} ({system} {release}; {machine})'.format(**appInfo())}


def fetchMessage(url):
    r = requests.get(url, headers=headers(), timeout=30)
    r.raise_for_status()

    data = r.json()
    if not isinstance(data, dict):
        raise ValueError('The message payload must be a dictionary, got {}'.format(type(data).__name__))

    messages = {}
    for key, value in data.items():
        if key in ['WS', 'WC', 'WV', 'WA'] and isinstance(value, list):
            messages[key] = value
        if key in ['SA', 'SP', 'FC', 'FT'] and isinstance(value, str):
            messages[key] = value

    if data and not messages:
        # The server answered, but nothing in the payload is a subscribed
        # type. Raising on purpose: handing it back as an ordinary empty
        # payload would look like fresh silence and wipe the cached messages.
        logger.error('Unknown message keys {} from {}'.format(sorted(data.keys()), url))
        raise ValueError('The message payload matched no subscribed type: {}'.format(sorted(data.keys())))

    return messages

def layerInfo(url):
    r = requests.get(url, headers=headers(), timeout=30)
    r.raise_for_status()

    data = r.json()
    if not isinstance(data, list):
        raise ValueError('The layer payload must be a list, got {}'.format(type(data).__name__))

    for layer in data:
        try:
            imageUrl = layer['image']
            req = requests.get(imageUrl, headers=headers(), timeout=30)
            layer['image'] = req.content
        except Exception as e:
            # A single image that fails is a partial success, not a failed
            # fetch: the layer stays, only without its picture.
            logger.warning('Failed to download layer image from {}, {}'.format(url, e))
            layer['image'] = None
    return data

def repoRelease(url):
    r = requests.get(url, headers=headers(), timeout=30)
    r.raise_for_status()

    data = r.json()
    if not isinstance(data, dict):
        raise ValueError('The release payload must be an object, got {}'.format(type(data).__name__))

    return data
