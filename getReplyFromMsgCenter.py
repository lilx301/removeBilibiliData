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
        for i in range(3):
            try:
                res = session.get(url, headers=headers,proxies= {},timeout=5)
                break
            except Exception as e:
                time.sleep(2 + random.random() * 3)  # 避免请求过快
        
        res.encoding = 'utf-8'
        res.raise_for_status()
        data = res.json()


        items = getObjWithKeyPath(data, 'data.items' )
        if not items:
            printD("No reply items found.")
            return 
        

        for item in items:
            reply_time = item.get('reply_time', 0)

            title = getObjWithKeyPath(item, 'item.title')
            oid = getObjWithKeyPath(item, 'item.subject_id')
            rpid = getObjWithKeyPath(item, 'item.target_id')
            msg = getObjWithKeyPath(item, 'item.target_reply_content')
            bvid = getBvidFromUri(getObjWithKeyPath(item, 'item.uri')) # 链接当做bvid
            if not  msg or msg == '':
                msg = title # 本身是root reply 
                title = None
            printD(f"Processing reply: {timeStamp2Str(reply_time)} \n{title}, oid: {oid}, rpid: {rpid}, msg: {msg} {timeStamp2Str(reply_time)}")


            itmInsert = {
                "rpid": rpid,
                "oid":oid,
                "bvid":bvid,    
                "title":title,
                "msg":msg,
                "ex1":"AtMe",
                "ctime":reply_time # 就把回复时间当做ctime吧
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
            time.sleep(2 + random.random() * 3)  # 避免请求过快
        
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
        oid = itm.get('id')

        db.insertCommentItem({
            "rpid": rpid,
            "oid": oid,
            "bvid": bvid,
            # "title": msg,  # Re-enable the title field
            "msg": msg,
            "ex1": "LikeMe",
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

    preTime = db.getConfig("get_like_me_msg_pre_time2" )

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
        
        printD(f"Cursor: {cursor}") 
        if not cursor or cursor.get('is_end') == True:
            if isDebug():
                # 结束，删掉进度
                config.removeConfig(keyForCusor)
            printD("No more LikeMe messages found.")
            break

        if newTime == 0:
            newTime = cursor.get('time')

        if cursor.get('time') < preTime:
            printD(f"Cursor time {cursor.get('time')} is older than preTime {preTime}, stopping.")
            break


        
        
        time.sleep(1 + random.random() * 3)  # 避免请求过快

    if newTime is not None and newTime > preTime:
        db.setConfig("get_like_me_msg_pre_time2", intV=newTime)

def getAllReply2MeMsg():
    """
    获取所有的@我回复
    """

    
     #进度当天有效，且只保存在本地，第一次运行在本地
    today=timeStamp2Str(int(time.time()))[0:10].replace('-', '')
    keyForCusor = f'localcfg_Rep_{today}'
    cursor = isDebug() and config.getJsonConfig(keyForCusor, NonIfNotExist=True) or None
    PAGE = 1

    preTime = db.getConfig("get_at_me_msg_pre_time2" )

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
        printD(f"Cursor: {cursor}") 
        if not cursor or cursor.get('is_end') == True:
            if isDebug():
                # 结束，删掉进度
                config.removeConfig(keyForCusor)
            printD("No more @me replies found.")
            break

        if newTime == 0:
            newTime = cursor.get('time')

        if cursor.get('time') < preTime:
            printD(f"Cursor time {cursor.get('time')} is older than preTime {preTime}, stopping.")
            break


        
        
        time.sleep(1 + random.random() * 3)  # 避免请求过快

    if newTime is not None and newTime > preTime:
        db.setConfig("get_at_me_msg_pre_time2", intV=newTime)
        

if __name__ == '__main__':
    
    try:
        db.initDB()

        print(db.getCommentsCountByType("AtMe"))
        print(db.getCommentsCountByType("LikeMe"))
        getAllLikeMeMsg()
    except KeyboardInterrupt as e:
        printD(e)
    else:
        print("EEE")
    finally:
        printD("XX")
        db.closeDb()



    



