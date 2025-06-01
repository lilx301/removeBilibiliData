import re
import time
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))
import refreshCookie
import config
import random
import requests
import json
from debug import printD, isDebug

from tool import timeStamp2Str
from tool import ymd2Stamp
from tool import getObjWithKeyPath
import db
from pushback import pushback

# 查询容差，两次运行4h间隔，这里设置5h
Query_Tolerance = 5 * 3600

UID = refreshCookie.getUid()


PreRepTimeKey = 'PreRepTimeKeyV2'
LikeTimeLine = 'LikeTimeLineV2'

# 查询历史记录
headers = {

        'Host': 'api.bilibili.com',
        'Origin': 'https://space.bilibili.com',
        'Referer': 'https://space.bilibili.com/21307077/fans/fans',
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' 


    }
session = refreshCookie.getReqWithCookie()


def getBvidFromUri(uri):
    if not uri:
        return None
    if uri.startswith('https://www.bilibili.com/video/'):
        return uri.split('/')[-1].split('?')[0]
    else:
        return uri

# oid，typecode
def getOidFromLikeItem(item):
    """
    从item中获取oid
    """
    if not item:
        return None,None



    # bilibili://video/123?page=0&comment_root_id=rpid
    # let oid be 123
    native_uri = getObjWithKeyPath(item, 'item.native_uri')
    if native_uri and native_uri.startswith('bilibili://video/'):
        native_uri = native_uri.split('bilibili://video/')[1]
        oid = native_uri.split('?')[0].split('&')[0]
        return oid,None
    
    if native_uri and native_uri.startswith('bilibili://comment/detail'):
        rpid = getObjWithKeyPath(item, 'item.item_id')
        # bilibili://comment/detail/xx/oid/rpid...
        try:
            arr2 = native_uri.split('/' + rpid)[0].split('/')
            return arr2[-1],arr2[-2]  # 返回oid和typecode
        except Exception as e:
            pass
    

    return None,None

def getOidFromReplyItem(item):
    if not item:
        return None,None



    # bilibili://video/123?page=0&comment_root_id=rpid
    # let oid be 123
    native_uri = getObjWithKeyPath(item, 'item.native_uri')
    if native_uri and native_uri.startswith('bilibili://video/'):
        native_uri = native_uri.split('bilibili://video/')[1]
        oid = native_uri.split('?')[0].split('&')[0]
        return oid,None
    
    if native_uri and native_uri.startswith('bilibili://comment/detail'):
        rpid = getObjWithKeyPath(item, 'item.item_id')
        # bilibili://comment/detail/xx/oid/rpid...
        try:
            arr2 = native_uri.split('/' + rpid)[0].split('/')
            return arr2[-1],arr2[-2]  # 返回oid和typecode
        except Exception as e:
            pass
    

    return None,None

def getMsgReplyMe(id = None,reply_time = None):
    """
    获取消息中心的@我回复
    """
    url = ''
    if id is None or reply_time is None:
        url = f'https://api.bilibili.com/x/msgfeed/reply?platform=web&build=0&mobi_app=web'
    else:   
        url = f'https://api.bilibili.com/x/msgfeed/reply?id={id}&reply_time={reply_time}&platform=web&build=0&mobi_app=web'

    try:
        for i in range(5):
            try:
                res = session.get(url, headers=headers,proxies= {},timeout=5)
                break
            except Exception as e:
                time.sleep(3 + random.random() )  # 避免请求过快
        

        
        res.encoding = 'utf-8'
        res.raise_for_status()
        data = res.json()


        items = getObjWithKeyPath(data, 'data.items' )
        if not items:
            printD("No reply items found.")
            return 
        

        for item in items:
            reply_time = item.get('reply_time', 0)
            oid = getObjWithKeyPath(item, 'item.subject_id')

            title = getObjWithKeyPath(item, 'item.title')
            
            rpid = getObjWithKeyPath(item, 'item.target_id')
            msg = getObjWithKeyPath(item, 'item.target_reply_content')
            
            bvid = getBvidFromUri(getObjWithKeyPath(item, 'item.uri')) # 链接当做bvid
            if not  msg or msg == '':
                msg = title # 本身是root reply 
                title = None
            printD(f"R {title}  msg: {msg} {timeStamp2Str(reply_time)}")

            
            typeCode = getObjWithKeyPath(item, 'item.business_id')

            itmInsert = {
                "rpid": rpid,
                "oid":oid,
                "bvid":bvid,    
                "title":title,
                "msg":msg,
                "ex1":"AtMe",
                "ex2": f"{typeCode}" if typeCode is not None else None,  # 添加typeCode
                "ctime":reply_time, # 就把回复时间当做ctime吧

                "json": json.dumps(item, ensure_ascii=False),  # 将item数据存储为JSON字符串 有些字段不知道什么意思，都存吧
            }

            # 尝试插入 
            db.insertCommentItem(itmInsert)


            # if reply_time < (int(time.time()) - Query_Tolerance):
            #     printD(f"Reply time {timeStamp2Str(reply_time)} is older than tolerance, skipping.")
            #     continue
            
        
        return  getObjWithKeyPath(data, 'data.cursor' )
    except requests.RequestException as e:
        printD(f"Request failed: {e}")

# 点赞
def getLikeMeMsg(id = None,like_time = None):
    """
    获取支持我的消息
    """

    url = 'https://api.bilibili.com/x/msgfeed/like?platform=web&build=0&mobi_app=web'

    if id is not None and like_time is not None:
        url += f'&id={id}&like_time={like_time}'



    res = None
    for i in range(3):
        try:
            res = session.get(url, headers=headers,proxies= {},timeout=5)
            break
        except Exception as e:
            time.sleep(3 + random.random() )  # 避免请求过快
        
    res.encoding = 'utf-8'
    res.raise_for_status()

    
    data = res.json()

    if data.get('code') != 0:
        printD("Error: Invalid response code.")
        return

    items = getObjWithKeyPath(data, 'data.total.items' )

    for itm in items:
        itmData = itm.get('item')
        if not itmData:
            printD("No item data found.")
            continue
        msg = itmData.get('title')
        bvid = getBvidFromUri(itmData.get('uri'))
        rpid = itmData.get('item_id')
        oid,typeCode = getOidFromLikeItem(itm)  # 获取oid
        if not oid:
            print("No oid found in item, skipping.")
            continue

        db.insertCommentItem({
            "rpid": rpid,
            "oid": oid,
            "bvid": bvid,
            # "title": msg,  # Re-enable the title field
            "msg": msg,
            "ex1": "LikeMe",
            "ex2": f"{typeCode}" if typeCode is not None else None,  # 添加typeCode
            "json": json.dumps(itm, ensure_ascii=False),  # 将item数据存储为JSON字符串
            "ctime": itmData.get('ctime', int(time.time()))  # 使用like_time或当前时间
        })
        printD(msg, bvid, )

    return getObjWithKeyPath(data, 'data.total.cursor' )



def getAllLikeMeMsg():
    """
    获取所有的点赞消息
    """

    #进度当天有效，且只保存在本地，第一次运行在本地
    today=timeStamp2Str(int(time.time()))[0:10].replace('-', '')
    keyForCusor = f'localcfg_{today}'



    cursor =  config.getJsonConfig(keyForCusor, NonIfNotExist=True) if isDebug() else None
    PAGE = 1

    preTime = db.getConfig(LikeTimeLine )

    preTime = 0 if preTime is None else preTime

    newTime = 0
    while True:
        print("LikeMe Page:", PAGE)
        PAGE += 1
        if cursor is None :
            cursor = getLikeMeMsg()
        else:
            cursor = getLikeMeMsg(cursor.get('id'), cursor.get('time'))

        if isDebug():
            config.saveJsonConfig(cursor, keyForCusor)
        
        printD(f"Cursor Like {PAGE }: {timeStamp2Str(cursor.get('time'))}\n{cursor}" ) 
        if not cursor or cursor.get('is_end') == True:
            printD("Ending like me retrieval.",cursor)
            if isDebug():
                # 结束，删掉进度
                config.removeConfig(keyForCusor)
            printD("No more LikeMe messages found.")
            db.setConfig(LikeTimeLine, intV=newTime)
            break

        if newTime == 0:
            newTime = cursor.get('time')

        if cursor.get('time') < preTime:
            printD(f"Cursor time {cursor.get('time')} is older than preTime {preTime}, stopping.")
            break


        
        
        time.sleep(1 + random.random() )  # 避免请求过快




        

def getAllReply2MeMsg():
    """
    获取所有的@我回复
    """

    
     #进度当天有效，且只保存在本地，第一次运行在本地
    today=timeStamp2Str(int(time.time()))[0:10].replace('-', '')
    keyForCusor = f'localcfg_Rep_{today}'
    cursor = isDebug() and config.getJsonConfig(keyForCusor, NonIfNotExist=True) or None
    PAGE = 0


    printD(f"Cursor for @me: {cursor}")
    # 

    preTime = db.getConfig(PreRepTimeKey )

    preTime = 0 if preTime is None else preTime

    newTime = 0
    while True:
        print("AtMe Page:", PAGE)
        PAGE += 1
        if cursor is None:
            cursor = getMsgReplyMe()
        else:
            cursor = getMsgReplyMe(cursor.get('id'), cursor.get('time'))
        
        config.saveJsonConfig(cursor, keyForCusor) if isDebug() else None
        printD(f"Cursor Rep {PAGE}: {timeStamp2Str(cursor.get('time'))} \n{cursor}" ) 
        if not cursor or cursor.get('is_end') == True:
            if isDebug():
                # 结束，删掉进度
                printD("Ending @me replies retrieval.",cursor)
                config.removeConfig(keyForCusor)
            printD("No more @me replies found.")
            db.setConfig(PreRepTimeKey, intV=newTime)
            break

        if newTime == 0:
            newTime = cursor.get('time')

        if cursor.get('time') < preTime:
            printD(f"Cursor time {cursor.get('time')} is older than preTime {preTime}, stopping.")
            break



        

        time.sleep(1 + random.random() )  # 避免请求过快


        
        

if __name__ == '__main__':
    
    try:
        db.initDB()

        
        getAllReply2MeMsg()
        if not isDebug():
            pushback("回复通知") 
        getAllLikeMeMsg()

        if not isDebug():
            pushback("点赞通知") 
        print(db.getCommentsCountByType("AtMe"))
        print(db.getCommentsCountByType("LikeMe"))
    except KeyboardInterrupt as e:
        printD(e)
    else:
        print("EEE")
    finally:
        printD("XX")
        db.closeDb()



    



