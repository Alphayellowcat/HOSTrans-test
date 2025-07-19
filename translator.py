import http.client
import hashlib
import urllib
import random
import json


class BaiduTranslator(object):
    def __init__(self, appid, secretkey):
        self.appid = appid
        self.secretKey = secretkey

    def trans(self, src_text, fromLang='auto', toLang='zh'):
        httpClient = None
        myurl = '/api/trans/vip/translate'
        salt = random.randint(32768, 65536)
        sign = self.appid + src_text + str(salt) + self.secretKey
        sign = hashlib.md5(sign.encode()).hexdigest()
        myurl = myurl + '?appid=' + self.appid + '&q=' + urllib.parse.quote(
            src_text) + '&from=' + fromLang + '&to=' + toLang + '&salt=' + str(
            salt) + '&sign=' + sign
        try:
            httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
            httpClient.request('GET', myurl)

            response = httpClient.getresponse()
            result_all = response.read().decode("utf-8")
            result = json.loads(result_all)

            return result['trans_result'][0]['dst']

        except Exception as e:
            return '翻译失败!'
        finally:
            if httpClient:
                httpClient.close()
