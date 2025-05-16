import re
import time
import sys
import os
import random

sys.path.insert(0, os.path.abspath("pylib"))
import requests 

import base64
import json
from aes import AEScoder 

import refreshCookie
refreshCookie.checkCookie()




cfgEnc =  open('cfg.json.enc').read()
enc=AEScoder(os.getenv('CFGKEY'))
jstring = enc.decrypt(cfgEnc)
jsonOBJ = json.loads(jstring)

Cookie64 = jsonOBJ['COOKIE64']
Cookie=base64.b64decode(Cookie64.encode('ascii')).decode('utf-8').strip()




csrf = re.findall(r'bili_jct=(\S+)', Cookie)[0].split(";")[0]
uid = re.findall(r'DedeUserID=(\S+)', Cookie)[0].split(";")[0]
# 粉丝数为0的时候 设置为0
Flag = 1

#print
print("print Start")
# 经测试 一天只能移除500个粉丝 超过500个会提示 {'code': -509, 'message': '请求过于频繁，请稍后再试', 'ttl': 1}

# 获取粉丝列表
def fansList():
    global Flag
    url = f"https://api.bilibili.com/x/relation/followers?vmid={uid}&pn=1&ps=20&order=desc&jsonp=jsonp"
    data = {
        'vmid': uid,
        'pn': 1,
        'ps': 20,
        'order': 'Desc',
        'jsonp': 'jsonp'
    }
    headers = {
        'Cookie': Cookie,
        'Host': 'api.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"
    }
    # 允许出错3次，避免长时间占用 ci
    ERRCOUNTMAX = 3
    while Flag:
        try:
            response = requests.request('get', url, params=data, headers=headers).json()
            fans_num = response['data']['total']
            if fans_num == 0:
                Flag = 0
            # 每页的粉丝数
            page_fans_num = len(response['data']['list'])
            for index in range(0, page_fans_num):
                ruid = response['data']['list'][index]['mid']
                uname = response['data']['list'][index]['uname']
                deleteFans(ruid, uname)
                # 休眠1s 免得删太快
                time.sleep(3 + random.random() * 3)
            print("粉丝还剩%d个" % fans_num)
            # print(response)
        except Exception as e:
            print(e)
            print("休眠5min")
            ERRCOUNTMAX =  ERRCOUNTMAX - 1
            if ERRCOUNTMAX <= 0:
                break
            time.sleep(30)
            pass


# 删除粉丝
def deleteFans(ruid, uname):
    url = "https://api.bilibili.com/x/relation/modify"
    data = {
        'fid': ruid,
        'act': 7,
        're_src': 11,
        'jsonp': 'jsonp',
        'csrf': csrf,
    }
    headers = {
        'Cookie': Cookie,
        'Host': 'api.bilibili.com',
        'Origin': 'https://space.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"

    }
    re = requests.request('post', url, data=data, headers=headers).json()
    if re['code'] == 0:
        print("删除粉丝:%d %s成功" % (ruid, uname))
    else:
        print("移除失败:", re)


if __name__ == '__main__':
    fansList()
