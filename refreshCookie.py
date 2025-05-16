import sys
import os
sys.path.insert(0, os.path.abspath("pylib"))
from aes import AEScoder
import json
import base64
import requests
import re
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
import binascii
import time


from requests.cookies import RequestsCookieJar
def set_cookies_from_string(session: requests.Session, cookie_str: str):
    jar = RequestsCookieJar()
    # cookie_str 例子: "a=1; b=2; c=3"
    items = cookie_str.split(';')
    for item in items:
        item = item.strip()
        if not item:
            continue
        if '=' in item:
            key, value = item.split('=', 1)
            jar.set(key.strip(), value.strip(),domain='.bilibili.com')
    session.cookies.update(jar)

key = RSA.importKey('''\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----''')
def get_content_by_id_regex(html: str, element_id: str) -> str | None:
    pattern = rf'<div id="{re.escape(element_id)}">(.*?)</div>'
    match = re.search(pattern, html, re.S)
    if match:
        return match.group(1).strip()
    return None
def getCorrespondPath(ts):
    cipher = PKCS1_OAEP.new(key, SHA256)
    encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
    return binascii.b2a_hex(encrypted).decode()





def getValueFromCookie(cookie, name):
    if not cookie:
        return None
    cookies = cookie.split(';')
    for item in cookies:
        item = item.strip()
        if item.startswith(name + '='):
            return item[len(name) + 1:]
    return None


def checkIfNeedUpdate(Cookie,ac_time_value):

    session = requests.Session()
    set_cookies_from_string(session,cookie_str=Cookie)


    bili_jct=getValueFromCookie(Cookie,'bili_jct')
    ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"

    url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
    data = {
        'csrf': bili_jct,
    }

    headers = {
        'User-Agent': ua
    }
 
    response = session.request('get', url, params=data, headers=headers).json()
   
    if response['code'] == 0:
        print("cookie 未过期")
        return
    
    print("刷新cookie")

    ts = round(time.time() * 1000)



    url=f"https://www.bilibili.com/correspond/1/{getCorrespondPath(ts)}"

    headers = {
        'Host': 'www.bilibili.com',
        'User-Agent': ua,
        
    }
    response = session.request('get', url, headers=headers)
    response.encoding = 'utf-8'
    html = response.text


    refreshToken=get_content_by_id_regex(html,'1-name')
    url='https://passport.bilibili.com/x/passport-login/web/cookie/refresh'
    data={
        'csrf':bili_jct,
        'refresh_csrf':refreshToken,
        'source':'main_web',
        'refresh_token':ac_time_value
    }

    response = session.request('post', url,params=data, headers={'User-Agent': ua})
    resJson = response.json()
    if resJson['code'] != 0:
        print('refreshX',response.json())    
        return
    
    
    newCookieStr=''
    for c in session.cookies:
        # print(f"name={c.name}, value={c.value}, domain={c.domain}, path={c.path}")
        newCookieStr= f"{newCookieStr}; {c.name}={c.value}"
    
    newCookieStr=newCookieStr[2:]

    bili_jctnew = getValueFromCookie(newCookieStr,'bili_jct')


    # 确认更新，会让旧的

    refreshToken=get_content_by_id_regex(html,'1-name')
    url='https://passport.bilibili.com/x/passport-login/web/confirm/refresh'
    data={
        'csrf':bili_jctnew,
        'refresh_token':ac_time_value
    }
    response = session.request('post', url,params=data, headers={'User-Agent': ua})

    print(response.json())
    return newCookieStr

def checkCookie():
    cfgEnc=''
    with open('cfg.json.enc') as f:
        cfgEnc =  f.read()


    enc=AEScoder(os.getenv('CFGKEY'))
    jstring = enc.decrypt(cfgEnc)
    jsonOBJ = json.loads(jstring)
    # 登录成功后 在 locastoage.getItem(ac_time_value)
    ac_time_value = jsonOBJ['ac_time_value']
    Cookie64 = jsonOBJ['COOKIE64']
    Cookie=base64.b64decode(Cookie64.encode('ascii')).decode('utf-8').strip()


    newCookie=checkIfNeedUpdate(Cookie,ac_time_value)
    if newCookie is None:
        return
    

    newCookieEnc=enc.encrypt(newCookie)
    jsonOBJ['COOKIE64'] = newCookieEnc
    jsonStrNew = json.dumps(jsonOBJ, indent=4)
    cipherNew = enc.encrypt(jsonStrNew)
    
    with open('cfg.json.enc','w') as f:
        f.write(cipherNew)

    


if __name__ == "__main__":
    checkCookie()
    
    
    
    