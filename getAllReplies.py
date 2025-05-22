import re
import time
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))
import refreshCookie
import config
import random


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

HistoryObj = config.getJsonConfig('history')

LIST = HistoryObj.get('list') 
if LIST is None:
    LIST = []
    HistoryObj['list'] = LIST


def sortList():
    LIST.sort(key=lambda p: p.get('view_at'),reverse=True)


sortList()

def addHistoryItmes(items):
    if items is not None and len(items) > 0:
        LIST.extend(items)

def save():
    sortList()
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
    if len(LIST) == 0:
        print("本地无数据，不能增量更新，直接 getAll 吧")
        return
    
    timeMax = LIST[0].get('view_at')

    queryTime = 0
    while 1:
       view_at,list =  getViewHistory(queryTime)
       if view_at > 0 and list is not None:
        newList = []
        for itm in list:
            if itm.get('view_at') is not None and itm.get('view_at') > timeMax:
                   newList.append(itm)
           
        
        print('新的历史记录',len(newList))
        if len(newList) > 0 :
            queryTime = view_at
            addHistoryItmes(newList)
            save()
            time.sleep(3 + random.random() * 3)
        else:
            break
            
           
              



# 全量查询，请先删掉 history.json.enc ,往后面查询
def getAll():

    S = 0
    lastViewTimeSec = HistoryObj.get("LastViewTimeSec")
    if  lastViewTimeSec is not None:
        S = lastViewTimeSec
    FLG = 1
    while FLG:
        S,newList =  getViewHistory(S)
        print(S)
        if S < 0:
            break

        addHistoryItmes(newList)
        HistoryObj['LastViewTimeSec'] = S
        HistoryObj['Count'] = len(LIST)
        save() 
        time.sleep(2.5 + random.random() * 3)
    
    save()



def  getObjWithKeyPath(obj,keypath):
    arr = keypath.split('.')
    sitem = obj
    for name in arr :
        sitem = sitem.get(name)
        if sitem is None:
            return None
    
    return sitem


QueryProgress = config.getJsonConfig("query_progress")

def updateProgres(time,page):
    if time is not None:
        QueryProgress['LastTimeAt'] = time
    if page is not None:
        QueryProgress['page'] = page
                # 保存查询进度
    config.saveJsonConfig(QueryProgress,'query_progress')



# 获取评论
def getRepiesInHistory(historyItem,initPagIdx):
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

    while 1:
        data  = {
            'type':type,
            'oid':oid,
            "pn":str(pageIdx)
        }
        res = session.get('https://api.bilibili.com/x/v2/reply',params=data,headers=headers)
        res.encoding  = "utf-8"

        jObj = None
        try:
            jObj = res.json()
        except Exception as e :
            print('获取评论失败....',oid,e)
            return -1,None

        
        # print(res.text)

        updateProgres(None,pageIdx)
        
        pageCount = getObjWithKeyPath(jObj,'data.page.count')
        list = getObjWithKeyPath(jObj,'data.replies')
        print('page', pageIdx,jObj.get("code"),jObj.get("ttl"),jObj.get("message"),pageCount,COUNT)
        if jObj.get("code") != 0:
            print('---------------ERROR ??',bt,oid,historyItem.get('view_at'))
            # print(historyItem,jObj)


        if list is not None:
            for itm in list:
                if itm.get('mid') == UID:
                    rList.append(itm)
        if list is not None and len(list) > 0 :
            COUNT += len(list)
        else:
            print(f"到末尾了，可能一些评论被吞了 {pageCount} -> {COUNT}" )
            break
        
        if COUNT >= pageCount:
            print('end')
            break
        
         
        pageIdx += 1
        time.sleep(4 + random.random() * 2)

     
    
    return 1,rList
    
 

def getAllReplies():
    

    RepConfig = config.getJsonConfig("comments2")
    listCmts = RepConfig.get('list')
    if listCmts is None:
        listCmts = []
        RepConfig['list'] = listCmts

    ta = QueryProgress.get('LastTimeAt')
    if ta is None:
        ta = 0
    
    # 从后往前

    initPage = QueryProgress.get('page') if     QueryProgress.get('page') is not None else 1
    print('beginAtPage',initPage)
    for idx in range(len(LIST) - 1, -1, -1):
        itm = LIST[idx]
        if itm.get('view_at') is not None and itm.get('view_at') > ta:
            pageIdx = 1 if initPage < 0 else initPage
            updateProgres(itm.get('view_at'),None)
            r,list = getRepiesInHistory(itm,pageIdx)
            initPage = -1; # 第一次才需要
            if r > 0:

                
                if len(list) > 0 :
                    for cmt in list:
                        cmtObj = {
                            "oid":cmt.get("oid_str"),
                            "rpid":cmt.get("rpid_str"),
                            "ctime":cmt.get("ctime"),
                            "msg":getObjWithKeyPath(cmt,'content.message')
                        }
                        listCmts.append(cmtObj)
                    
                    config.saveJsonConfig(RepConfig,'comments2')
            
            time.sleep(20 + random.random() * 10)

        

 
    print('get all')

     
if __name__ == '__main__':

    getAll()
    updateHistory()
    getAllReplies()

    



