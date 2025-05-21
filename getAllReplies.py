import re
import time
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))
import refreshCookie
import config
import random
# refreshCookie.checkCookie()
print("---------------------------------\n\n")
print("由于b站，没有接口获取自己的评论，这里轮序历史记录，为防止太耗时github")
print("\n\n---------------------------------")

# 查询历史记录
headers = {

        'Host': 'api.bilibili.com',
        'Origin': 'https://space.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"

    }
session = refreshCookie.getReqWithCookie()

HistoryObj = config.getJsonConfig('history')

LIST = HistoryObj.get('list') 
if LIST is None:
    LIST = []
    HistoryObj['list'] = LIST

def save():
    config.saveJsonConfig(HistoryObj,'history')


def getViewHistory(timeSec = 0):
    data  = {
        'view_at':str(timeSec),
        'ps':"25",
        "business":"article"
    }
    res = session.get('https://api.bilibili.com/x/web-interface/history/cursor',params=data,headers=headers)
    res.encoding  = "utf-8"
    # print(res.text)
    try:
        resObj = res.json()
        if resObj is None:
            return -1
        if resObj['data'] is None:
            return -1
        if resObj['data']['list'] is None:
            # err
            return -2
        if len(resObj['data']['list']) == 0 :
            return -3
        
        for itm in resObj['data']['list']:
            obj = itm.get('history')
            if obj is not None:
                obj['view_at'] = itm.get('view_at')
                LIST.append(obj)
        return resObj['data']['list'][-1]['view_at']

    except Exception as e:
        return -1


# 全量查询，请先删掉 history.json.enc
def getAll():

    nowT = int(time.time())
    HistoryObj['QueryTime'] = nowT


    S = 0
    lastViewTimeSec = HistoryObj.get("LastViewTimeSec")
    if  lastViewTimeSec is not None:
        S = lastViewTimeSec
    FLG = 1
    while FLG:
        S =  getViewHistory(S)
        print(S)
        if S < 0:
            break

        HistoryObj['LastViewTimeSec'] = S
        HistoryObj['Count'] = len(LIST)
        save() 
        time.sleep(0.5 + random.random())
    
    save()



     
if __name__ == '__main__':
    print('获取历史记录')
    getAll()


