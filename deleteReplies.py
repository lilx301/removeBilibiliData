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
import datetime
import refreshCookie
# refreshCookie.checkCookie()


import config

from debug import printD
import db



jsonOBJ = config.getJsonConfig('cfg')

Cookie64 = jsonOBJ['COOKIE64']
Cookie=base64.b64decode(Cookie64.encode('ascii')).decode('utf-8').strip()


csrf = re.findall(r'bili_jct=(\S+)', Cookie)[0].split(";")[0]
uid = re.findall(r'DedeUserID=(\S+)', Cookie)[0].split(";")[0]



#print
print("print Start")



GCOUNT=1

def saveItem(item):
    key=f"RP-{item['dyn']['oid']}-{item['rpid']}" 
    if commensMap.get(key) is None:
        commensMap[key] = item.get('message')
        return 1
    
    return 0


# 删除一个评论
def deleteReplyItem(replyItem):
    #
    #           {
	# 			"message":" MESG",
	# 			"rank":1,
	# 			"rpid":"",
	# 			"time":1744000000,
	# 			"dyn":
	# 			{
	# 				"oid":"id",
	# 				"type":1
	# 			},
	# 			"parent":{}
	# 		},


    key=f"RP-{replyItem['dyn']['oid']}-{replyItem['rpid']}" 
    if commensMap.get(key)is not None and ']-[del-' in  commensMap.get(key):
        return -1
    

    url = "https://api.bilibili.com/x/v2/reply/del"
    data = {
        'type': replyItem['dyn']['type'],
        'oid': replyItem['dyn']['oid'],
        'rpid': replyItem['rpid'],
        'csrf': csrf,
    }
    
    headers = {
        'Cookie': Cookie,
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36",
        'Origin': 'https://space.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',

    }
    resObj=requests.request('post', url, data=data, headers=headers,timeout=5)
    re = resObj.json()
    
    #     0：成功
    # -101：账号未登录
    # -102：账号被封停
    # -111：csrf校验失败
    # -400：请求错误
    # -403：权限不足
    # -404：无此项
    # -509：请求过于频繁
    # 12002：评论区已关闭
    # 12009：评论主体的type不合法
    # 12022：已经被删除了 
    #  ...
    if re['code'] == 0:
        global GCOUNT
        print("删除评论 成功" , GCOUNT)
        GCOUNT = GCOUNT + 1

        date_str = ''
        try: 
            dt = datetime.datetime.fromtimestamp(replyItem['time'])
            date_str = dt.strftime('%Y-%m-%d')
        except Exception as e :
            date_str = '--'

    
    # 不要改格式，后面可能会导入
        commensMap[key] = f"{replyItem['message']}  ------[{date_str}]-[del-{datetime.datetime.now().strftime('%Y-%m-%d')}]"
        return 1

    else:
        print("移除失败:", re)
        return 0
    

def startDelete(timeStamp):
    STOP=0

    PAGE=1
    while STOP == 0:
        
        res = getReplyList(PAGE)
        PAGE += 1

        print(res['data']['cursor'])
        list = res['data']['replies']
        if list is  None or len(list) == 0:
            print('获取列表失败')
            return
        

        for item in reversed(list):
            t =item.get('time')
            if t is not None:
                #  item['time'] < timeStamp:
                if t > timeStamp:
                    printD('keep',item.get('message'))
                    saveItem(item)
                try:
                    i = deleteReplyItem(item)
                    if i == 1:
                        saveJson(commensMap,'comments')
                    if i == -1:
                        continue

                    time.sleep( 2 + random.random() * 3)
                except Exception as e:
                    print("发生异常：", e)
                    STOP = 1
                    break
        

        saveJson(commensMap,'comments')
        # 存一下
        try :
            if res['data']['cursor']['is_end'] == True:
                STOP=1
        except Exception as e :
            print(e)
            STOP = 1

        time.sleep(5 + random.random() * 10)
        
    
        




    
def saveJson(jsonOBJ,name):
    config.saveJsonConfig(jsonOBJ,name)
     
    

commensMap = config.getJsonConfig('comments')

 
if __name__ == '__main__':
    
    try:
        db.initDB()
        nowSecStamp = int(time.time())
    # 删除时间超过7天的评论
        print('删除时间超过7天的评论')
        startDelete(nowSecStamp - 24 * 3600 * 7)
    except KeyboardInterrupt as e:
        printD(e)
    else:
        print("EEE")
    finally:
        printD("XX")
        db.closeDb()

   
    
