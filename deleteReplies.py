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
import tool
from pushback import pushback


jsonOBJ = config.getJsonConfig('cfg')

Cookie64 = jsonOBJ['COOKIE64']
Cookie=base64.b64decode(Cookie64.encode('ascii')).decode('utf-8').strip()


csrf = re.findall(r'bili_jct=(\S+)', Cookie)[0].split(";")[0]
uid = re.findall(r'DedeUserID=(\S+)', Cookie)[0].split(";")[0]



#print
print("print Start")



GCOUNT=1
GCOUNTALL = 0 
 

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


    key=f"RP-{replyItem['oid']}-{replyItem['rpid']}" 
    

    url = "https://api.bilibili.com/x/v2/reply/del"
    data = {
        'type': '1' if  replyItem.get('ex2') is None else f"{replyItem['ex2']}",
        'oid': replyItem['oid'],
        'rpid': replyItem['rpid'],
        'csrf': csrf,
    }
    
    headers = {
        'Cookie': Cookie,
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36",
        'Origin': 'https://space.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',

    }
    for _ in range(3):
        try:
            # 可能会被封IP
            resObj=requests.request('post', url, data=data, headers=headers,timeout=5)
            break
        except requests.exceptions.RequestException as e:
            printD("请求异常，重试:", e)
            time.sleep(2 + random.random() * 2)
    
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
    printD(re)
    flag = 1 if re.get('code') == 0 else re.get('code')
    db.updateCommentFlag(str( replyItem['oid']),str(replyItem.get("rpid")),flag)
    if re['code'] == 0:
        global GCOUNT,GCOUNTALL
        print("删除评论 成功" , GCOUNT, '/', GCOUNTALL)
        
        GCOUNT = GCOUNT + 1

        date_str = ''
        try: 
            dt = datetime.datetime.fromtimestamp(replyItem['time'])
            date_str = dt.strftime('%Y-%m-%d')
        except Exception as e :
            date_str = '--'

        return 1

    else:

        print("移除失败:", re )
        printD("移除失败:",replyItem )
        return 0


def checkLoopShoudStop(list2Del,preList):
    if list2Del is None or len(list2Del) == 0:
        return True
    
    if preList is None or len(preList) == 0:
        return False
    
    # 判断两个 list 是否相同，相同就停止，防止死循环
    if len(list2Del) != len(preList):
        return False
    
    first = list2Del[0]
    last = list2Del[-1]

    first2 = preList[0]
    last2 = preList[-1]

    if first['oid'] == first2['oid'] and first['rpid'] == first2['rpid'] and last['oid'] == last2['oid'] and last['rpid'] == last2['rpid']:
        print('循环检测：相同，停止')
        return True
    else:
        printD('循环检测：不同，继续')
        return False
    




def startDelete(timeStamp):
    global GCOUNTALL,GCOUNT
    STOP=0

    GCOUNTALL= db.getUndeletedCommentsCount(timeStamp)
    preList = None
    while STOP == 0:
        
        list2Del = db.getUndeletedComments(timeStamp)
        if checkLoopShoudStop(list2Del, preList):
            break
        preList = list2Del
 
        if list2Del is  None or len(list2Del) == 0:
            print('无--未删除的评论')
            STOP = 1
            break

        printD('待删除评论数量:', len(list2Del))
        

        for item in list2Del:
            t =item.get('ctime')
            if t is not None:
                #  item['time'] < timeStamp:
                if t > timeStamp:
                    printD('keep',item.get('msg'),tool.timeStamp2Str(item.get('ctime')))
                try:
                    printD('删除评论', item.get('msg'), '时间:',   tool.timeStamp2Str(item.get('ctime')))
                    i = deleteReplyItem(item)
                    if i == 1:
                        printD('删除成功', item.get('msg'),item.get('bvid'),tool.timeStamp2Str(item.get('ctime')))
                    if i == -1:
                        continue

                    time.sleep( 1 + random.random() )
                except Exception as e:
                    print("发生异常：", e)
                    STOP = 1
                    break
            
            time.sleep(0.3 + random.random() )
        
        
    
        if GCOUNT % 500 == 499:
            pushbackMsg = f"删除评论数量：{GCOUNT} / {GCOUNTALL}"
            pushback(pushbackMsg)




 
if __name__ == '__main__':
    
    try:
        db.initDB()
        nowSecStamp = int(time.time())
        print('删除时间超过6天的评论')
        startDelete(nowSecStamp - 24 * 3600 * 3)
    except KeyboardInterrupt as e:
        printD(e)
    else:
        print("EEE")
    finally:
        printD("XX")
        db.closeDb()

   
    
