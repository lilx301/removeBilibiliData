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


# 私有辅助方法：构建请求参数
def _buildReplyRequestParams(type, oid, pageIdx):
    """构建评论查询请求参数"""
    return {
        'type': type,
        'oid': oid,
        'sort': '0',
        'pn': str(pageIdx)
    }


# 私有辅助方法：发送请求并处理重试
def _fetchReplyWithRetry(session, url, params, headers, maxRetries, oid):
    """发送评论查询请求并处理重试逻辑"""
    NetRetryMax = maxRetries
    while True:
        try:
            res = session.get(url, params=params, headers=headers, proxies={}, timeout=10)
            res.encoding = "utf-8"
            return res
        except Exception as e:
            printD(e)
            printD('网络失败 ... 2s 后重试')
            if NetRetryMax > 0:
                NetRetryMax = NetRetryMax - 1
                time.sleep(1.5 + random.random())
                continue
            else:
                return None


# 私有辅助方法：解析响应JSON
def _parseReplyResponse(res, oid):
    """解析评论查询响应JSON"""
    if res is None:
        return None, -1
    
    jObj = None
    try:
        jObj = res.json()
        return jObj, 0
    except Exception as e:
        printD('获取评论失败....', oid, e)
        return None, -100


# 私有辅助方法：提取评论数据
def _extractReplyData(jObj):
    """从响应中提取评论数据"""
    if jObj is None:
        return None, None, ''
    
    pageCount = getObjWithKeyPath(jObj, 'data.page.count')
    list = getObjWithKeyPath(jObj, 'data.replies')
    lastTime = ''
    if list is not None and len(list) > 0 and list[-1].get('ctime') is not None:
        lastTime = timeStamp2Str(list[-1].get('ctime'))
    
    return pageCount, list, lastTime


# 私有辅助方法：检查错误码
def _checkReplyErrorCode(jObj, bt, oid, viewAt):
    """检查响应错误码，返回 (should_return, return_value)"""
    if jObj is None:
        return True, (-100, None)
    
    if jObj.get("code") != 0:
        printD('---------------ERROR ??', bt, oid, viewAt)
        db.updateHistoryLatestCommentTime(oid, jObj.get("code"))
        return True, (0, None)
    
    return False, None


# 私有辅助方法：更新首次时间
def _updateFirstTime(firstTime, list, pageIdx):
    """更新首次评论时间"""
    if list is not None and firstTime == 0:
        # 中断重新载入的，直接当做最新时间
        if len(list) == 0 or pageIdx > 1:
            return int(time.time())
        else:
            return list[0].get('ctime')
    return firstTime


# 私有辅助方法：过滤自己的评论
def _filterMyComments(list, uid, callback, historyItem, rList):
    """过滤出自己的评论并调用回调"""
    if list is None:
        return []
    
    filterList = []
    for itm in list:
        if itm.get('mid_str') == uid:
            rList.append(itm)
            filterList.append(itm)
    
    if len(filterList) > 0:
        callback(filterList, historyItem)
    
    return filterList


# 私有辅助方法：检查终止条件
def _checkStopConditions(list, pageCount, COUNT, timeLst, preQueryLatestTime, historyItem, Query_Tolerance, seq):
    """检查是否应该停止查询，返回 (should_stop, reason)
    注意：早于观看时间的检查已由自适应算法处理，此处不再重复检查
    """
    # 列表为空则退出
    if list is None or len(list) == 0:
        return True, "列表为空"
    
    # COUNT >= pageCount 则退出
    if COUNT >= pageCount:
        printD('end')
        return True, "已查询完所有评论"
    
    # 是否超过上次查询，避免大查询
    if timeLst is not None and timeLst < preQueryLatestTime:
        printD("已经超过上次的了查询，skip")
        return True, "超过上次查询时间"
    
    # 注意：早于观看时间的检查已由 _updatePageIndexWithAdaptive 处理，此处不再重复检查
    # 这样可以避免在快速模式下提前 break，确保能够回退到起点进行精确轮询
    
    return False, None


# 私有辅助方法：更新页码（自适应算法）
def _updatePageIndexWithAdaptive(pageIdx, list, historyItem, preQueryIndex, isPullback, seq, Query_Tolerance):
    """自适应二分定位算法：跳跃式+回退式双模式查询，返回 (newPageIdx, newIsPullback, action)
    action: 'continue' 表示需要回退并 continue, 'break' 表示应该 break, 'normal' 表示继续正常流程
    """
    currentQueryIndex = pageIdx
    oldestTime = list[-1].get('ctime') if (list and len(list) > 0) else None
    historyTime = historyItem.get('view_at') - Query_Tolerance if historyItem.get('view_at') is not None else None
    
    # 判断是否到达历史边界（最老评论时间早于目标时间）
    if list is None or len(list) == 0 or (oldestTime is not None and historyTime is not None and oldestTime < historyTime):
        if currentQueryIndex - preQueryIndex <= 1:
            # 细粒度查询下仍未找到更多评论，停止
            printD(f"[{seq}] 已到达历史边界，停止查询")
            return pageIdx, isPullback, 'break'  # 应该 break
        else:
            # 回退到安全位置，开始细粒度扫描
            newPageIdx = preQueryIndex + 1
            newIsPullback = True
            printD(f"[{seq}] 回退模式: 从页 {preQueryIndex} → {newPageIdx}")
            return newPageIdx, newIsPullback, 'continue'  # 应该 continue（回退）
    else:
        # 还在新评论区域，继续推进
        # 检查是否需要强制进入pullback模式：如果当前步长不等于1，并且最老评论进入到历史时间+10h内
        currentStep = currentQueryIndex - preQueryIndex
        shouldForcePullback = False
        
        if historyTime is not None and oldestTime is not None:
            historyTimeUpperBound = historyTime + 10 * 3600
            if currentStep != 1 and oldestTime >= historyTime - 10*3600 and oldestTime <= historyTimeUpperBound:
                shouldForcePullback = True
                printD(f"[{seq}] 接近历史时间边界（最老评论在历史时间±10h内），进入pullback模式精细查找")
        
        # 如果满足条件，强制进入pullback模式
        effectiveIsPullback = isPullback or shouldForcePullback
        
        if effectiveIsPullback:
            if shouldForcePullback:
                newPageIdx = preQueryIndex + 1  # 回退模式：细粒度步长
                printD(f"[{seq}] 接近历史时间边界，回退到安全位置: {currentQueryIndex} → {newPageIdx}")
                return newPageIdx, effectiveIsPullback, 'continue'  # 回退操作，需要 continue
            else:
                newPageIdx = currentQueryIndex + 1   # 回退模式：细粒度步长
                printD(f"[{seq}] 细粒度扫描: {currentQueryIndex} → {newPageIdx}")
        else:
            newPageIdx = currentQueryIndex + 10  # 正常模式：粗粒度步长
            printD(f"[{seq}] 快速推进: {currentQueryIndex} → {newPageIdx}")
        
        return newPageIdx, effectiveIsPullback, 'normal'  # 继续正常流程


# 获取评论
# 由于 同一个视频，观看多次只有一个记录，这里直接暴力查出所有

def getRepiesInHistory(historyItem,initPagIdx,seq,callback):
    pageIdx = 1 if initPagIdx is None else  initPagIdx
    COUNT = 0
    rList = []
    
    # 自适应二分定位算法状态变量
    preQueryIndex = pageIdx      # 上一次查询的页码
    isPullback = False           # 是否处于回退模式


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

    printD(f"getReplies[{seq}] {bt} view_at: {timeStamp2Str(historyItem.get('view_at') -  random.randint(1000,Query_Tolerance))}")
    printD(f"{oid},{historyItem.get('title')}   \t{timeStamp2Str(historyItem.get('view_at'))}")

    NetRetryMax = 5

    # 上次最新时间戳
    preQueryLatestTime = historyItem.get('newest_cmt_time')
    preQueryLatestTime = 0 if preQueryLatestTime is None else preQueryLatestTime

    firstTime = 0
    while 1:
        # 构建请求参数
        data = _buildReplyRequestParams(type, oid, pageIdx)

        printD(pageIdx)
        
        if pageIdx % 10 == 9:
            printD(f"{historyItem.get('title')}  {timeStamp2Str(historyItem.get('view_at'))}")
        
        # 发送请求并处理重试
        res = _fetchReplyWithRetry(session, 'https://api.bilibili.com/x/v2/reply', data, headers, NetRetryMax, oid)
        if res is None:
            return -1, None
        
        # 解析响应JSON
        jObj, error_code = _parseReplyResponse(res, oid)
        if error_code != 0:
            return error_code, None
        
        # 更新进度
        updateProgres(None, page=pageIdx)
        
        # 提取评论数据
        pageCount, list, lastTime = _extractReplyData(jObj)
        
        # 打印查询日志
        printD(f' [{seq}] page:{pageIdx: 4d} mode:{"pullback" if isPullback else "jump"} code:{jObj.get("code")} ttl:{jObj.get("ttl")} msg:{jObj.get("message")} {COUNT: 4d}-{pageCount} T:{lastTime}')
        
        # 检查错误码
        should_return, return_value = _checkReplyErrorCode(jObj, bt, oid, historyItem.get('view_at'))
        if should_return:
            return return_value
        
        # 更新首次时间
        firstTime = _updateFirstTime(firstTime, list, pageIdx)
        
        # 过滤自己的评论
        _filterMyComments(list, UID, callback, historyItem, rList)
        
        # 更新计数
        if list is not None and len(list) > 0:
            COUNT += len(list)
        
        # 获取最老评论时间
        timeLst = list[-1].get("ctime") if (list is not None and len(list) > 0) else None
        
        # 先执行自适应算法，判断是否需要回退或停止（即使列表为空也要执行，以便回退）
        newPageIdx, newIsPullback, action = _updatePageIndexWithAdaptive(pageIdx, list, historyItem, preQueryIndex, isPullback, seq, Query_Tolerance)
        if action == 'continue':
            # 如果需要回退，直接 continue，不检查终止条件
            pageIdx = newPageIdx
            isPullback = newIsPullback
            continue
        elif action == 'break':
            # 如果应该停止，直接 break
            break
        
        # 检查终止条件（仅在正常流程下检查）
        should_stop, reason = _checkStopConditions(list, pageCount, COUNT, timeLst, preQueryLatestTime, historyItem, Query_Tolerance, seq)
        if should_stop:
            break
        
        # 正常模式下更新 preQueryIndex
        preQueryIndex = pageIdx
        pageIdx = newPageIdx
        isPullback = newIsPullback
        
        time.sleep(2 + random.random() * 1)

    if firstTime is None or firstTime <= 0:
        firstTime = int(time.time())

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
            if itm.get('view_at') is not None and itm.get('view_at') >= ta or 1:
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
 
                time.sleep(1 + random.random() )

        

        pushbackMsg = f"已查{_counter}历史"

        pushback(pushbackMsg)

        

        



    

 
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
        try:
            print("从AICU")
            getReplyListFromAICU()
        except Exception as e:
            print('eeee',e)

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



    



