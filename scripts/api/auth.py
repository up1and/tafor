import json
import base64
import binascii
import datetime

import requests

from io import BytesIO

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from PIL import Image


with open('auth.json') as f:
    authorization = json.load(f)

api_key = authorization['api_key']
secret_key = authorization['secret_key']
user = authorization['amsc_user']
password = authorization['amsc_password']


def _pad_string(value):
    block_size = 16
    value = value.encode('utf-8')
    return value + (block_size - len(value) % block_size) * chr(block_size - len(value) % block_size).encode('utf-8')

def encrypt(message):
    key = b'12345678900000001234567890000000'
    iv = b'1234567890000000'
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    encrypted_text = encryptor.update(_pad_string(message)) + encryptor.finalize()
    return binascii.b2a_hex(encrypted_text).decode('utf-8')


class BaiduAip(object):

    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.token = None
        self.expire = datetime.datetime.utcnow()

    def generate_token(self):
        url = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={}&client_secret={}'.format(
            self.api_key, self.secret_key)
        response = requests.get(url, timeout=10)
        if response:
            data = response.json()
            self.token = data['access_token']
            self.expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=data['expires_in'])

    def recognize(self, image):
        if self.token is None or self.expire < datetime.datetime.utcnow():
            self.generate_token()

        url = 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic'
        data = {
            'image': base64.b64encode(image.getvalue()).decode()
        }
        params = {
          'access_token': self.token
        }
        response = requests.post(url, params=params, data=data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['words_result'][0]['words']


class AmscSession(object):

    def __init__(self, user, password, valuator):
        self.user = user
        self.password = password
        self.session = None
        self.valuator = valuator

    def captcha_image(self):
        url = 'http://amsc.net.cn/Page/Default/CreateImg.aspx'
        response = requests.get(url, stream=True, timeout=10)
        session = response.headers['Set-Cookie'].split(';')[0]
        gif = Image.open(response.raw)
        image = BytesIO()
        gif.save(image, 'PNG')
        return image, session

    def login(self, captcha, session):
        url = 'http://amsc.net.cn/Page/Default/LoginHandler.ashx'
        params = {
            'cmd': 'PanDuanLogin',
            'UserName': encrypt(self.user),
            'Password': encrypt(self.password),
            'YanZhengMa': encrypt(captcha),
            'Type': encrypt('China')
        }
        headers = {
            'Cookie': session
        }
        response = requests.post(url, headers=headers, params=params, timeout=30)
        if response.text == 'true':
            return session

    def update(self):
        try:
            image, session = self.captcha_image()
            captcha = self.valuator.recognize(image)
            self.session = self.login(captcha, session)
            return self.session
        except Exception:
            pass

valuator = BaiduAip(api_key, secret_key)
amsc = AmscSession(user, password, valuator)


if __name__ == '__main__':
    amsc.update()
    print(amsc.session)