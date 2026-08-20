import logging

import requests

from tafor.core.utils.common import appInfo

logger = logging.getLogger('tafor.client')


_headers = {
    'User-Agent': 'Tafor/{version}+{revision} ({system} {release}; {machine})'.format(**appInfo())
}


def fetchMessage(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, dict):
                raise ValueError('The message data type is incorrect, please pass in data of dictionary type')

            messages = {}
            for key, value in data.items():
                if key in ['WS', 'WC', 'WV', 'WA'] and isinstance(value, list):
                    messages[key] = value
                if key in ['SA', 'SP', 'FC', 'FT'] and isinstance(value, str):
                    messages[key] = value

            return messages
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error('Failed to fetch message from {}, {}'.format(url, e))

    return {}

def layerInfo(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, list):
                raise ValueError('The layer data type is incorrect, please pass in data of list type')

            for layer in data:
                try:
                    imageUrl = layer['image']
                    req = requests.get(imageUrl)
                    layer['image'] = req.content
                except Exception as e:
                    layer['image'] = None
            return data
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error('Failed to fetch cloud layer from {}, {}'.format(url, e))

    return []

def repoRelease(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error('Failed to get the latest version information from {}, {}'.format(url, e))

    return {}