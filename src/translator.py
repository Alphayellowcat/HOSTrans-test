import copy
import hashlib
import http.client
import json
import os
import random
import time
import urllib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'translator_config.json')


TRANSLATOR_SPECS = {
    'baidu': {
        'label': '百度翻译',
        'fields': [
            {'key': 'appid', 'label': 'App ID', 'required': True},
            {'key': 'secretkey', 'label': '密钥', 'required': True, 'secret': True},
        ],
    },
    'deepl': {
        'label': 'DeepL',
        'fields': [
            {'key': 'auth_key', 'label': 'Auth Key', 'required': True, 'secret': True},
            {'key': 'api_host', 'label': 'API Host', 'required': False, 'default': 'api-free.deepl.com'},
        ],
    },
    'youdao': {
        'label': '有道翻译',
        'fields': [
            {'key': 'app_key', 'label': 'App Key', 'required': True},
            {'key': 'app_secret', 'label': 'App Secret', 'required': True, 'secret': True},
        ],
    },
    'papago': {
        'label': 'Papago',
        'fields': [
            {'key': 'client_id', 'label': 'Client ID', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'required': True, 'secret': True},
        ],
    },
}


def _build_default_config():
    providers = {}
    for provider_key, spec in TRANSLATOR_SPECS.items():
        provider_fields = {}
        for field in spec['fields']:
            provider_fields[field['key']] = field.get('default', '')
        providers[provider_key] = provider_fields
    return {
        'provider': 'baidu',
        'providers': providers,
    }


def _ensure_config_defaults(config):
    defaults = _build_default_config()
    if 'provider' not in config:
        config['provider'] = defaults['provider']
    providers = config.setdefault('providers', {})
    for provider_key, fields in defaults['providers'].items():
        provider_fields = providers.setdefault(provider_key, {})
        for field_key, default_value in fields.items():
            provider_fields.setdefault(field_key, default_value)
    return config


def load_config():
    config = _build_default_config()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as fh:
                file_config = json.load(fh)
            config.update({k: v for k, v in file_config.items() if k in config})
            config['providers'].update(file_config.get('providers', {}))
        except (OSError, json.JSONDecodeError):
            pass
    else:
        legacy_path = os.path.join(BASE_DIR, 'baiduAPI.txt')
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, 'r', encoding='utf-8') as fh:
                    lines = fh.readlines()
                lines = [line.strip() for line in lines if line.strip()]
                if len(lines) >= 2:
                    config['providers']['baidu']['appid'] = lines[0]
                    config['providers']['baidu']['secretkey'] = lines[1]
            except OSError:
                pass
    return _ensure_config_defaults(copy.deepcopy(config))


def save_config(config):
    config = _ensure_config_defaults(copy.deepcopy(config))
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as fh:
            json.dump(config, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass


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

        except Exception:
            return '翻译失败!'
        finally:
            if httpClient:
                httpClient.close()


class DeepLTranslator(object):
    def __init__(self, auth_key, api_host='api-free.deepl.com'):
        self.auth_key = auth_key
        self.api_host = api_host or 'api-free.deepl.com'

    def _map_lang(self, lang):
        mapping = {
            'zh': 'ZH',
            'en': 'EN',
            'kor': 'KO',
        }
        return mapping.get(lang.lower(), lang.upper())

    def trans(self, src_text, fromLang='auto', toLang='zh'):
        conn = None
        params = {
            'auth_key': self.auth_key,
            'text': src_text,
            'target_lang': self._map_lang(toLang),
        }
        if fromLang != 'auto':
            params['source_lang'] = self._map_lang(fromLang)
        try:
            conn = http.client.HTTPSConnection(self.api_host)
            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            conn.request('POST', '/v2/translate', urllib.parse.urlencode(params), headers)
            response = conn.getresponse()
            if response.status != 200:
                return '翻译失败!'
            payload = response.read().decode('utf-8')
            data = json.loads(payload)
            translations = data.get('translations', [])
            if not translations:
                return '翻译失败!'
            return translations[0].get('text', '翻译失败!')
        except Exception:
            return '翻译失败!'
        finally:
            if conn:
                conn.close()


class YoudaoTranslator(object):
    def __init__(self, app_key, app_secret):
        self.app_key = app_key
        self.app_secret = app_secret

    def _map_lang(self, lang):
        mapping = {
            'zh': 'zh-CHS',
            'en': 'en',
            'kor': 'ko',
        }
        return mapping.get(lang.lower(), lang)

    def _truncate(self, text):
        if text is None:
            return ''
        size = len(text)
        if size <= 20:
            return text
        return text[:10] + str(size) + text[-10:]

    def trans(self, src_text, fromLang='auto', toLang='zh'):
        conn = None
        salt = str(random.randint(1, 65536))
        curtime = str(int(time.time()))
        params = {
            'q': src_text,
            'appKey': self.app_key,
            'salt': salt,
            'curtime': curtime,
            'signType': 'v3',
            'from': 'auto' if fromLang == 'auto' else self._map_lang(fromLang),
            'to': self._map_lang(toLang),
        }
        sign_str = self.app_key + self._truncate(src_text) + salt + curtime + self.app_secret
        params['sign'] = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        try:
            conn = http.client.HTTPSConnection('openapi.youdao.com')
            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            conn.request('POST', '/api', urllib.parse.urlencode(params), headers)
            response = conn.getresponse()
            if response.status != 200:
                return '翻译失败!'
            payload = response.read().decode('utf-8')
            data = json.loads(payload)
            if data.get('errorCode') != '0':
                return '翻译失败!'
            translation = data.get('translation')
            if isinstance(translation, list) and translation:
                return ''.join(translation)
            if isinstance(translation, str) and translation:
                return translation
            return '翻译失败!'
        except Exception:
            return '翻译失败!'
        finally:
            if conn:
                conn.close()


class PapagoTranslator(object):
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def _map_lang(self, lang):
        mapping = {
            'zh': 'zh-CN',
            'zh-cn': 'zh-CN',
            'zh-tw': 'zh-TW',
            'en': 'en',
            'kor': 'ko',
            'ko': 'ko',
        }
        return mapping.get(lang.lower(), lang)

    def _build_headers(self):
        return {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
        }

    def _detect_lang(self, text):
        conn = None
        try:
            conn = http.client.HTTPSConnection('openapi.naver.com')
            params = urllib.parse.urlencode({'query': text})
            conn.request('POST', '/v1/papago/detectLangs', params, self._build_headers())
            response = conn.getresponse()
            if response.status != 200:
                return None
            payload = response.read().decode('utf-8')
            data = json.loads(payload)
            return data.get('langCode')
        except Exception:
            return None
        finally:
            if conn:
                conn.close()

    def trans(self, src_text, fromLang='auto', toLang='zh'):
        conn = None
        source_lang = fromLang
        if fromLang == 'auto':
            detected = self._detect_lang(src_text)
            if detected:
                source_lang = detected
            else:
                source_lang = 'ko'
        source_lang = 'auto' if source_lang == 'auto' else self._map_lang(source_lang)
        target_lang = self._map_lang(toLang)
        params = urllib.parse.urlencode({
            'source': source_lang,
            'target': target_lang,
            'text': src_text,
        })
        try:
            conn = http.client.HTTPSConnection('openapi.naver.com')
            conn.request('POST', '/v1/papago/n2mt', params, self._build_headers())
            response = conn.getresponse()
            if response.status != 200:
                return '翻译失败!'
            payload = response.read().decode('utf-8')
            data = json.loads(payload)
            message = data.get('message', {})
            result = message.get('result', {}) if isinstance(message, dict) else {}
            translated = result.get('translatedText')
            if translated:
                return translated
            return '翻译失败!'
        except Exception:
            return '翻译失败!'
        finally:
            if conn:
                conn.close()


def create_translator():
    config = load_config()
    provider = config.get('provider', 'baidu')
    provider_settings = config.get('providers', {}).get(provider, {})
    if provider == 'baidu':
        appid = provider_settings.get('appid', '').strip()
        secretkey = provider_settings.get('secretkey', '').strip()
        if appid and secretkey:
            return BaiduTranslator(appid, secretkey)
    elif provider == 'deepl':
        auth_key = provider_settings.get('auth_key', '').strip()
        api_host = provider_settings.get('api_host', '').strip() or 'api-free.deepl.com'
        if auth_key:
            return DeepLTranslator(auth_key, api_host)
    elif provider == 'youdao':
        app_key = provider_settings.get('app_key', '').strip()
        app_secret = provider_settings.get('app_secret', '').strip()
        if app_key and app_secret:
            return YoudaoTranslator(app_key, app_secret)
    elif provider == 'papago':
        client_id = provider_settings.get('client_id', '').strip()
        client_secret = provider_settings.get('client_secret', '').strip()
        if client_id and client_secret:
            return PapagoTranslator(client_id, client_secret)
    return None
