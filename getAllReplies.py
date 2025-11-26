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
from debug import printD, isDebug

from tool import timeStamp2Str
from tool import ymd2Stamp
from tool import getObjWithKeyPath
import db
from pushback import pushback

# 查询容差，两次运行4h间隔，这里设置5h
Query_Tolerance = 5 * 3600

# 步长调整阈值：当最老评论时间 < 访问时间 + 此阈值时，步长改为1
STEP_SIZE_THRESHOLD_HOURS = 3

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

                titleA = itm.get('title')
                
                obj['title'] = titleA
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
    










def setLastCmtTime(oid,time):
    db.updateHistoryLatestCommentTime(oid,time)


def updateProgres(time,page,oid=None):
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

    print(f"getReplies[{seq}] {bt} view_at: {timeStamp2Str(historyItem.get('view_at') -  random.randint(1000,Query_Tolerance))}",)
    printD(f"{oid},{historyItem.get('title')}   \t{timeStamp2Str(historyItem.get('view_at'))}")

    NetRetryMax = 5

# 上次最新时间戳
    preQueryLatestTime =  historyItem.get('newest_cmt_time')
    preQueryLatestTime = 0 if preQueryLatestTime is None else preQueryLatestTime

    firstTime = 0
    stepSize = 10  # 初始步长为10
    lastPageIdx = pageIdx  # 保存上一次页码，初始化为当前页码
    isFirstQuery = True  # 标记是否是首次查询
    emptyResultCount = 0  # 连续空结果计数，防止无限循环
    while 1:
        lastPageIdx = pageIdx  # 保存当前页码
        data  = {
            'type':type,
            'oid':oid,
            'sort':'0',
            # 'ps':"20",
            "pn":str(pageIdx)
        }

        printD(f"{historyItem.get('title')}  {timeStamp2Str(historyItem.get('view_at'))}" )
        try:
            res = session.get('https://api.bilibili.com/x/v2/reply',params=data,headers=headers,proxies={},timeout=10)
        except Exception as e:
            print(e)
            print('网络失败 ... 2s 后重试')
            if NetRetryMax > 0:
                NetRetryMax = NetRetryMax - 1
                time.sleep(1.5 + random.random() )
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
        
        # 检查 jObj 是否为 None
        if jObj is None:
            print('API 响应解析失败，jObj 为 None')
            return -100, None
        
        # print(res.text)

        updateProgres(None,page=pageIdx)
        
        pageCount = getObjWithKeyPath(jObj,'data.page.count')
        list = getObjWithKeyPath(jObj,'data.replies')
        lastTIme = ''
        if list is not None and len(list) > 0 and list[-1].get('ctime') is not None:
            lastTIme =  timeStamp2Str(list[-1].get('ctime'))
        print(f' [{seq}] page:{pageIdx: 4d} code:{jObj.get("code")} ttl:{jObj.get("ttl")} msg:{jObj.get("message")} {COUNT: 4d}-{pageCount} T:{lastTIme}')
        if jObj.get("code") != 0:
            print('---------------ERROR ??',bt,oid,historyItem.get('view_at'))
            db.updateHistoryLatestCommentTime(oid,jObj.get("code"))

            return 0, None

            # print(historyItem,jObj)


        if list is not None:
            if  firstTime == 0 :
                # 中断重新载入的，直接当做最新时间
                if len(list) == 0 or pageIdx > 1:
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
        
        # 动态步长调整逻辑
        if list is None or len(list) == 0:
            # 查询结果为空，回退并设置步长为1
            emptyResultCount += 1
            # 防止无限循环：如果连续多次查询结果都为空，终止查询
            if emptyResultCount > 10:
                print(f"连续 {emptyResultCount} 次查询结果为空，终止查询以避免无限循环")
                break
            
            if isFirstQuery:
                # 首次查询结果为空，直接设置步长为1，不需要回退
                stepSize = 1
                printD(f'[步长调整] 首次查询结果为空，步长改为1')
            else:
                # 非首次查询结果为空，回退并设置步长为1
                stepSize = 1
                pageIdx = lastPageIdx  # 回退到上次位置，下次循环会从 lastPageIdx + stepSize 开始
                printD(f'[步长调整] 查询结果为空，回退到 page {lastPageIdx}，步长改为1，下次从 page {lastPageIdx + stepSize} 开始')
        elif list is not None and len(list) > 0:
            # 有结果时重置空结果计数
            emptyResultCount = 0
            # 获取最老评论时间
            oldestCtime = list[-1].get("ctime")
            viewAt = historyItem.get('view_at')
            thresholdTime = None
            if viewAt is not None:
                thresholdTime = viewAt + STEP_SIZE_THRESHOLD_HOURS * 3600  # 访问时间 + 阈值小时
            
            # 判断是否需要调整步长
            if oldestCtime is not None and thresholdTime is not None and oldestCtime < thresholdTime:
                # 最老评论时间 < 访问时间+阈值小时，设置步长为1
                stepSize = 1
                if isFirstQuery:
                    # 首次查询就满足条件，直接设置步长为1，不需要回退
                    printD(f'[步长调整] 首次查询最老评论时间 {timeStamp2Str(oldestCtime)} < 访问时间+{STEP_SIZE_THRESHOLD_HOURS}h {timeStamp2Str(thresholdTime)}，步长改为1')
                else:
                    # 非首次查询满足条件，回退并设置步长为1
                    pageIdx = lastPageIdx  # 回退到上次位置，下次循环会从 lastPageIdx + stepSize 开始
                    printD(f'[步长调整] 最老评论时间 {timeStamp2Str(oldestCtime)} < 访问时间+{STEP_SIZE_THRESHOLD_HOURS}h {timeStamp2Str(thresholdTime)}，回退到 page {lastPageIdx}，步长改为1，下次从 page {lastPageIdx + stepSize} 开始')
        
        # 首次查询后，标记为非首次
        isFirstQuery = False
        
        # 如果查询结果为空，判断是否应该结束
        if list is None or len(list) == 0:
            # 如果总评论数为0或None，说明这个视频/文章根本没有评论，直接结束
            if pageCount is None or pageCount == 0:
                print(f"该视频/文章没有评论，结束查询 (pageCount: {pageCount})")
                break
            # 否则，说明可能是步长太大跳过了某些页，已经通过步长调整逻辑回退了
            # 更新 pageIdx 并继续查询（跳过时间检查）
            pageIdx += stepSize
            time.sleep(2 + random.random() * 1)
            continue
        
        # COUNT 是累计获取的评论数，pageCount 是总评论数
        # 如果 pageCount 为 None，跳过此检查
        if pageCount is not None and COUNT >= pageCount:
            print('end')
            break

        # 是否超过上次查询，避免大查询
        timeLst = list[-1].get("ctime")
        if timeLst is not None and timeLst < preQueryLatestTime:
            print("已经超过上次的了查询，skip")
            break

        # 早于观看时间段评论忽略，这样可能一个视频多次观看会遗漏，但是，就这样吧，希望不会有太多，aicu 能兜底的吧
        viewAtStr = historyItem.get('ex2')
        if 0 and viewAtStr is not None and len(viewAtStr) > 0:
            oldestTimeStr = viewAtStr.split(';')[0]
            oldestTime = int(oldestTimeStr)
            # 给一个7h 的debug，防止两次 查看同一次
            if timeLst is not None and timeLst < oldestTime - Query_Tolerance:
                print("早于观看时间的评论忽略吧22...")
                break
        else:
            if timeLst is not None and historyItem.get('view_at') is not None and timeLst < historyItem.get('view_at') - Query_Tolerance:
                print("早于观看时间的评论忽略吧...")
                break

        
        
        pageIdx += stepSize
        time.sleep(2 + random.random() * 1)

    printD('firstTime',firstTime)
    # firstTime 初始化为 0，如果为 0 则使用当前时间
    timeToSet = firstTime if firstTime > 0 else int(time.time())
    setLastCmtTime(oid, timeToSet)
    return 1, rList


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
        insertRep(cmt,historyItm.get('title'),{'bvid':historyItm.get('bvid')})


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

    ta,preQueryOid, initPage= db.getCurrentQueryProgress()
    printD('BEGIN',timeStamp2Str(ta),preQueryOid,initPage)
    if ta is None:
        ta = 0
    
    # 从后往前

    initPage = 1 if  initPage is  None else initPage
    print('beginAtPage',initPage)
    _counter = 0

    PRELIST = None

    ALLNeedQuery = db.getUnQueryHistoryCount()
    while 1:
        hisList = db.getUnqueryHistory()
        if checkNeedStop(hisList,PRELIST):
            break
        PRELIST = hisList
        if hisList is None or len(hisList) == 0:
            break
        for  itm in hisList:
            _counter += 1
            # 如果历史记录的 view_at 小于等于上次查询的时间，说明已经查询过了，跳过
            if ta is not None and ta > 0 and itm.get('view_at') is not None and itm.get('view_at') <= ta:
                printD(f'跳过已查询的历史记录: {itm.get("oid")} view_at: {timeStamp2Str(itm.get("view_at"))} <= {timeStamp2Str(ta)}')
                continue
            
            if _counter == 1 and itm.get('oid') == preQueryOid and initPage > 0:
                pageIdx = initPage
                printD('continue ',_counter, itm.get('oid'),itm.get('view_at'),pageIdx)
            else:
                pageIdx = 1
                    
                  
                    

            updateProgres(itm.get('view_at'),None,itm.get("oid"))
              
            print(f"seq {_counter} / {ALLNeedQuery}")
            r,_ = getRepiesInHistory(itm,pageIdx,seq=_counter,callback=dealCommentOnHistory)
            initPage = -1; # 第一次才需要
            if r < 0:
                print("发生错误，停止",r)
                return
            
            # 记录最后处理的历史记录时间，用于下次查询时跳过已查询的记录
            if itm.get('view_at') is not None:
                updateProgres(itm.get('view_at'), None, None)  # 只更新时间，不更新 oid 和 pageNo
 
            time.sleep(1 + random.random() )

        

        pushbackMsg = f"已查{_counter}历史"

        pushback(pushbackMsg)
    
    # 所有历史记录查询完成
    # currentQueryTime 已经在处理每个历史记录时更新，最后的值就是最后处理的历史记录时间
    # 下次查询时会自动从该时间继续，跳过已查询的记录
    lastTime = db.getConfig('currentQueryTime')
    if lastTime is not None:
        print(f'所有历史记录查询完成，最后查询时间: {timeStamp2Str(lastTime)}，下次查询将从该时间继续')
    else:
        print('所有历史记录查询完成')

        

        



    

 
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


    


# 获取屏幕列表
def getReplyListFromAICUAtPage(idx,uid=UID):

    url = f"https://n.kr7y.workers.dev/https://api.aicu.cc/api/v3/search/getreply?uid={uid}&pn={idx}&ps=300&mode=0&keyword="
    if isDebug():
        url = f"https://api.aicu.cc/api/v3/search/getreply?uid={uid}&pn={idx}&ps=300&mode=0&keyword="
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
    print(f"now:\t{timeStamp2Str(nowSec)}\npre\t{ timeStamp2Str(timePre)if timePre is not None else None}")
    isFullQuery = False
    print("查询AICU评论",nowSec - timePre)
    if timePre is not None and    nowSec - timePre > 5 * 60 * 60 * 24:
        print("5 天全量查询一次")
        isFullQuery = True
        db.setConfig('last-time-query-aicu2', intV=nowSec)
    else:
        print("增量查询")
        pass
    
    
    
    

    newestCtime = db.getNewestAICUCommentCtime()
    printD(timeStamp2Str(newestCtime))

    for pg in range(1,100000):
        try:
            res = getReplyListFromAICUAtPage(pg)
        except Exception as e:
            print("Error occurred",e)
            break
        

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

        t = list[-1]
        if not isFullQuery and  t is not None and  t.get('time')  is not None and t.get('time') < newestCtime:
            print("停止增量更新")
            return
        time.sleep(1.5)


def mainfunc():

    # importRepliesViaAICUData()
    # testGetRep()

    taskType = sys.argv[1] if len(sys.argv) > 1 else None

    if taskType is None :
        
        print("没有参数 1 更新历史记录，2 更新评论")

    elif taskType == '1':
        print("更新历史记录")
        updateHistory()
        getAllHistories()
    elif taskType == '2':
        print("更新评论")
        # try:
        #     print("从AICU")
        #     getReplyListFromAICU()
        # except Exception as e:
        #     print('eeee',e)

        try:
            print("根据历史记录查询")
            getAllReplies()
        except Exception as e:
            print('eeee22',e)
        

        
    

   

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



    



