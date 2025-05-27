import re
import time
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))
import refreshCookie
import config
import random
import datetime
import calendar
import requests
from debug import printD

from tool import timeStamp2Str
from tool import ymd2Stamp
from tool import getObjWithKeyPath
import db


UID = refreshCookie.getUid()


print("---------------------------------\n\n")
print("由于b站，没有接口获取自己的评论，这里轮序历史记录，为防止太耗时github")
print("\n\n---------------------------------")

# 查询历史记录
headers = {

        'Host': 'api.bilibili.com',
        'Origin': 'https://space.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' 


    }
session = refreshCookie.getReqWithCookie()





def addHistoryItmes(items):
    if items is not None and len(items) > 0:
        for itm in items:
            oid = itm.get('oid')
            if oid is not None:
                db.insertHistoryItem(itm)
 

def getViewHistory(timeSec = 0):
    data  = {
        'view_at':str(timeSec),
        'ps':"25",
        "business":"article"
    }
    res = session.get('https://api.bilibili.com/x/web-interface/history/cursor',params=data,headers=headers,timeout=20)
    res.encoding  = "utf-8"
    try:
        resObj = res.json()
        if resObj is None:
            return -1,None
        if resObj['data'] is None:
            return -1,None
        if resObj['data']['list'] is None:
            # err
            return -2,None
        if len(resObj['data']['list']) == 0 :
            return -3,None
        
        resultList = []
        for itm in resObj['data']['list']:
            obj = itm.get('history')
            if obj is not None:
                obj['view_at'] = itm.get('view_at')
                resultList.append(obj)
        return resultList[-1]['view_at'],resultList

    except Exception as e:
        return -1,None



def updateHistory():
    if db.getHistoryCount() == 0:
        print("本地无数据，不能增量更新，直接 getAll 吧")
        return
    
    
    near,far = db.getHistoryTimeRange()
    printD(near,timeStamp2Str(near))
    
    queryTime = 0
    while 1:
       view_at,list =  getViewHistory(queryTime)
       if view_at > 0 and list is not None:
        newList = []
        for itm in list:
            if itm.get('view_at') is not None and itm.get('view_at') > near:
                   newList.append(itm)
           
        
        print('新的历史记录',len(newList))
        if len(newList) > 0 :
            printD(newList[0].get('title'))
            queryTime = view_at
            addHistoryItmes(newList)
            time.sleep(3 + random.random() * 3)
        else:
            break
            
           
              



# 全量查询，请先删掉 history.json.enc ,往后面查询
def getAllHistories():

    S = 0    
    xx,lastViewTimeSec = db.getHistoryTimeRange()
    printD(timeStamp2Str(xx))
    printD(timeStamp2Str(lastViewTimeSec))

    if  lastViewTimeSec is not None:
        S = lastViewTimeSec
    FLG = 1
    while FLG:
        S,newList =  getViewHistory(S)
        print(timeStamp2Str(S))
        if S < 0:
            break

        addHistoryItmes(newList)
        time.sleep(1 + random.random() )
    






QueryProgress = config.getJsonConfig("query_progress")

LstCmtTimeForOid = config.getJsonConfig("LstCmtTimeForOid")

def setLastCmtTime(oid,time):
    db.updateHistoryLatestCommentTime(oid,time)
def getLastCmtTime(oid):
    t = LstCmtTimeForOid.get(oid)
    return t if t is not None else 0

def updateProgres(time,page,reverse = True,oid=None):
    db.updateQueryCommentCtx(time,oid,page)



# 获取评论
# 由于 同一个视频，观看多次只有一个记录，这里直接暴力查出所有
def getRepiesInHistory(historyItem,initPagIdx,seq,callback):
    pageIdx = 1 if initPagIdx is None else  initPagIdx
    COUNT = 0
    rList = []

    # archive: "1", pgc: "1", live: "1", article: "1", cheese: "课程"
    bt =  historyItem.get('business') 
    type =  '1' 
    if 'live' == bt:
        type = '8'
    elif 'cheese' == bt:
        type = '33'
    # archive：稿件
    # pgc：剧集（番剧 / 影视）
    # live：直播
    # article-list：文集
    # article：文章

    oid = f"{historyItem.get('oid')}"

    print(f"getReplies[{seq}]",bt)
    printD(f"{oid},{historyItem.get('part')}   \n{timeStamp2Str(historyItem.get('view_at'))}")

    NetRetryMax = 5

# 上次最新时间戳
    preQueryLatestTime =  getLastCmtTime(oid)

    firstTime = 0
    while 1:
        data  = {
            'type':type,
            'oid':oid,
            'sort':'0',
            "pn":str(pageIdx)
        }
        print(f"query[{seq}]",pageIdx  )
        if pageIdx % 10 == 9 :
            printD(f"{historyItem.get('part')}  {timeStamp2Str(historyItem.get('view_at'))}" )
        try:
            res = session.get('https://api.bilibili.com/x/v2/reply',params=data,headers=headers,proxies={},timeout=10)
        except Exception as e:
            print(e)
            print('网络失败 ... 2s 后重试')
            if NetRetryMax > 0:
                NetRetryMax = NetRetryMax - 1
                time.sleep(2 + random.random() * 3)
                continue
            else:
                return -1,None

            
        res.encoding  = "utf-8"

        jObj = None
        try:
            jObj = res.json()
        except Exception as e :
            print('获取评论失败....',oid,e)
            return -100,None

        
        # print(res.text)

        updateProgres(None,page=pageIdx)
        
        pageCount = getObjWithKeyPath(jObj,'data.page.count')
        list = getObjWithKeyPath(jObj,'data.replies')
        print('    page', pageIdx,jObj.get("code"),jObj.get("ttl"),jObj.get("message"),pageCount,COUNT)
        if jObj.get("code") != 0:
            print('---------------ERROR ??',bt,oid,historyItem.get('view_at'))
            db.updateHistoryLatestCommentTime(oid,1)

            return 0, None,

            # print(historyItem,jObj)


        if list is not None:
            if  firstTime == 0 :
                if len(list) == 0:
                    firstTime = int(time.time())
                else:
                    firstTime = list[0].get('ctime')
                

            filterList = []
            for itm in list:
                if itm.get('mid_str') == UID:
                    rList.append(itm)
                    filterList.append(itm)
            
            if len(filterList) > 0 :
                callback(filterList,historyItem)

        if list is not None and len(list) > 0 :
            COUNT += len(list)
        else:
            # print(f"到末尾了，可能一些评论被吞了 {pageCount} -> {COUNT}" )
            break
        
        if COUNT >= pageCount:
            print('end')
            break

        # 是否超过上次查询，避免大查询
        timeLst = list[-1].get("ctime")
        if timeLst is not None and timeLst < preQueryLatestTime:
            print("已经超过上次的了查询，skip")
            break
        
        pageIdx += 1
        time.sleep(1 + random.random() * 1)

    if firstTime is not None and firstTime > 0 :
        setLastCmtTime(oid,firstTime)
    return 1,rList


g_cmt_idx = {}


 
def insertRep(itm,title,extraItm=None):
    cmtObj =  {
                    "oid":itm.get("oid_str"),
                    "rpid":itm.get("rpid_str"),
                    "ctime":itm.get("ctime"),
                    "msg":getObjWithKeyPath(itm,'content.message'),
                    "title":title
                }
    
    if extraItm is not None:
        cmtObj = { ** cmtObj , ** extraItm}


    db.insertCommentItem(cmtObj)
    

def dealCommentOnHistory(listMyComent,historyItm):
    for cmt in listMyComent:
        insertRep(cmt,historyItm.get('part'),{'bvid':historyItm.get('bvid')})


def checkNeedStop(list,preList):
    """
    检查是否需要停止查询
    如果当前查询的评论和上次查询的评论相同，则停止
    """
    if list is None or len(list) == 0:
        return True
    
    if preList is None or len(preList) == 0:
        return False
    
    # 判断两个 list 是否相同，相同就停止，防止死循环
    if len(list) != len(preList):
        return False
    
    first = list[0]
    last = list[-1]

    first2 = preList[0]
    last2 = preList[-1]

    if first['oid'] == first2['oid']  and last['oid'] == last2['oid']  :
        printD('循环检测：相同，停止')
        return True
    else:
        printD('循环检测：不同，继续')
        return False

def getAllReplies(Revers=True):

    ta,oid, initPage= db.getCurrentQueryProgress()
    printD('BEGIN',timeStamp2Str(ta),oid,initPage)
    if ta is None:
        ta = 0
    
    # 从后往前

    initPage = 1 if  initPage is  None else initPage
    print('beginAtPage',initPage)
    _counter = 0

    PRELIST = None
    while 1:
        hisList = db.getUnqueryHistory()
        if checkNeedStop(hisList,PRELIST):
            break
        PRELIST = hisList
        if hisList is None or len(hisList) == 0:
            break
        for  itm in hisList:
            _counter += 1
            if itm.get('view_at') is not None and itm.get('view_at') >= ta or 1:
                pageIdx = 1 if initPage < 0 or ta != itm.get('view_at') else initPage

                updateProgres(itm.get('view_at'),None,itm.get("oid"))
                print(f"seq {_counter} {len(hisList)}")
                r,_ = getRepiesInHistory(itm,pageIdx,seq=_counter,callback=dealCommentOnHistory)
                initPage = -1; # 第一次才需要
                if r < 0:
                    print("发生错误，停止",r)
                    return
 
                time.sleep(1 + random.random() )

        

        



    

 
    print('get all')

def testGetRep():
    print("test")
 
    his = db.getUnqueryHistory()[0]
    printD(his)
    r,list = getRepiesInHistory(his,1,seq=1,callback=dealCommentOnHistory)
    if r < 0:
        print("发生错误，停止")
        return

    print('EE')


def importRepliesViaAICUData():
    print("从aicu 也就是 comments.json.enc 读取 评论，载入到 comments2")

    cmtMap = config.getJsonConfig('comments')
    keys = cmtMap.keys()
    for key in keys:
        if not key.startswith("RP-"):
            continue

        arr = key.split('-')
        if len(arr ) == 3:
            oid = arr[1]
            rpid = arr[2]
            value = cmtMap.get(key)
            ctime = None
            dtime = None
            flag = None
            msg = value
            if ']-[del-' in value:
                parts = re.split(r'  ------\[|\]-\[del-|\]$', value)
                ctime = ymd2Stamp(parts[1])
                dtime = ymd2Stamp(parts[2])
                flag = 1
                msg = parts[0]
                
            

            #已经删了
            itm = {
                "oid": oid,
                "rpid": rpid,
                "ctime": ctime,
                'delTime':dtime,
                "flag":flag,
                "msg":msg
            }

            # {
            #         "oid":itm.get("oid_str"),
            #         "rpid":itm.get("rpid_str"),
            #         "ctime":itm.get("ctime"),
            #         "msg":getObjWithKeyPath(itm,'content.message'),
            #         "title":title
            #     }

            insertRep({"oid":oid,"rpid":rpid},None,itm)

    


# 获取屏幕列表
def getReplyListFromAICUAtPage(idx,uid=UID):
    url = f"https://n.kr7y.workers.dev/https://api.aicu.cc/api/v3/search/getreply?uid={uid}&pn={idx}&ps=300&mode=0&keyword="
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"
    }
    # 允许出错3次，避免长时间占用 ci

    re = requests.request('get', url, headers=headers,timeout=5)
    re.encoding = 'utf-8'
    return re.json()    
             

def getReplyListFromAICU():
    timePre = db.getConfig('last-time-query-aicu2')
    nowSec = int(time.time())
    print(f"now\n{timeStamp2Str(nowSec)}\nprevious{ timeStamp2Str(timePre)if timePre is not None else None}")
    if timePre is not None and    nowSec - timePre < 15 * 60 * 60 * 24:
        print("最近15天已经查询过了，跳过")
        return
    
    db.setConfig('last-time-query-aicu2', intV=nowSec)
    pg = 1
    while 1:
        res = getReplyListFromAICUAtPage(pg)
        pg += 1

        print(res['data']['cursor'])
        list = res['data']['replies']
        
        if list is  None or len(list) == 0:
            print('获取列表失败',pg)
            return
        print('list',len(list))

        for itm in list:
            # {'rpid': '268', 'message': 'a message', 'time': 182222, 'rank': 1, 'parent': {}, 'dyn': {'oid': '1104552116', 'type': 1}}
            itmInsert = {
                ** itm,
                "oid":getObjWithKeyPath(itm,"dyn.oid"),
                "msg":itm.get("message"),
                "ex1":"AICU",
                "ctime":itm.get('time'),
                "ex2":getObjWithKeyPath(itm,"dyn.type"),
            }

            db.insertCommentItem(itmInsert)
            # {
        #     "oid": "1111",
        #     "rpid": "1111",
        #     "ctime": 1700000000,
        #     "msg": "xxxxx",
        #     "title": 't',
        #     "delTime": 1747584000,
        #      "bvid": 'bv'
        #     "flag": 1
        # },

        time.sleep(1.5)


def mainfunc():

    # importRepliesViaAICUData()
    # testGetRep()
    updateHistory()
    getAllHistories()
    
    getReplyListFromAICU()
    getAllReplies()

if __name__ == '__main__':
    try:
        db.initDB()
        mainfunc()
    except KeyboardInterrupt as e:
        printD(e)
    else:
        print("EEE")
    finally:
        printD("XX")
        db.closeDb()



    



