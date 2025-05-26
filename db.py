import sqlite3
import time
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))
import refreshCookie
import config
import random
import datetime
import calendar
from debug import printD
import json
import tool 

conn = None
cursor = None

def closeDb():
    if conn is not None:
        cursor.close()
        conn.close()
        


def initDB():
    global conn
    global cursor
    if conn == None:
        # 连接数据库（如果不存在会自动创建）
        conn = sqlite3.connect('data/bilidata.db')
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        

        # 创建表（如果还没有）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            
            key TEXT PRIMARY KEY ,
            ivalue INTEGER,
            svalue TEXT,
            db_create_time DATETIME DEFAULT (CURRENT_TIMESTAMP)
        )
        ''')

        # 提交事务
        conn.commit()


        '''
         {
            "oid": 11122, 这里存成string
            "epid": 0,
            "bvid": "BV1XXE",
            "page": 1,
            "cid": 29,
            "part": "标题",
            "business": "archive",
            "dt": 1,
            "view_at": 17470000  sec
        },
         '''
        # 历史记录
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS histories (

            oid TEXT  PRIMARY KEY  ,
            bvid TEXT,
            title TEXT ,
            business TEXT,
            view_at INTEGER,
            newest_cmt_time INTEGER DEFAULT 0,
                       
            ex1 TEXT,
            ex2 TEXT,
            ex3 TEXT,
            json TEXT ,
            db_create_time DATETIME DEFAULT (CURRENT_TIMESTAMP)
    
        )
        ''')
        # 提交事务
        conn.commit()




         # 回复
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments   (
            key TEXT PRIMARY KEY  NOT NULL,
            oid TEXT  ,
            bvid TEXT,
            title TEXT,
            
            rpid TEXT NOT NULL,
            msg TEXT  NOT NULL,
            ctime INTEGER,
            deltime INTEGER,
            flag INTEGER,   
            json TEXT     ,
            db_create_time DATETIME DEFAULT (CURRENT_TIMESTAMP)
        )
        ''')
        # 提交事务
        conn.commit()

 
def setConfig(KEY:str , strV : str = None, intV :int = None):
    if strV is not None and intV is not None:
        raise RuntimeError(f"{KEY} 只能设置 strV 或者  intV 中的一个")
        
    
    cursor.execute("SELECT * FROM config WHERE key = ? limit 1", (KEY,))
    row = cursor.fetchone()
    if row is None :
        cursor.execute("INSERT INTO config (key, ivalue,svalue) VALUES (?, ? , ?)", (KEY, intV,strV))
        conn.commit()
    else:
        obj = dict(row)
        if strV is not None:
            if obj.get('svalue') == strV:
                return
        if intV is not None:
            if obj.get('ivalue') == intV:
                return
        
        # 更新
        cursor.execute("UPDATE config SET svalue = ? , ivalue = ?  WHERE key = ?", (strV, intV,KEY))
        conn.commit()


def getConfig(KEY):
    cursor.execute("SELECT ivalue,svalue  FROM config WHERE key = ? limit 1", (KEY,))
    row = cursor.fetchone()
    if row is None:
        return None

    mp = dict(row)
    if mp.get('svalue') is not None:
        return mp.get('svalue')
    return mp.get('ivalue')




def _checkRowExsit(key,tableName,keyname):

    cursor.execute(f""" 
                    SELECT db_create_time from "{tableName}" where {keyname} = ? limit 1
                   """,
                   (key,)
                   )
    exsist = cursor.fetchone()
    if exsist is not None:
        return True
    return False


def insertHistoryItem(item):
    '''
     {
            "oid": 1111,
            "epid": 0,
            "bvid": "BV133",
            "page": 1,
            "cid": 122,
            "part": "标题",
            "business": "archive",
            "dt": 1,
            "view_at": 174000000
        },
    '''

    oid = item.get('oid')
    if oid is None:
        print("没有oid？？")
        return
    
    oidStr = str(oid)


    if _checkRowExsit(oidStr,'histories','oid'):
        # 存在就 更新 时间
        updateHistoryLatestCommentTime(oidStr,item.get('view_at'))

        return

    #  oid  bvid title, business view_at newest_cmt_time json          
    cursor.execute('''
        INSERT OR IGNORE INTO histories (oid , bvid , title, business ,view_at ,newest_cmt_time , json) VALUES (?,?,?,?,?,?,?)
    ''',(oidStr,item.get('bvid'),item.get('part'),item.get('business'),item.get('view_at'),item.get('newest_cmt_time'),json.dumps(item, indent=4,ensure_ascii=False),))
    
    conn.commit()

def insertCommentItem(item):
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
    oid = item.get('oid')
    rpid = item.get('rpid')
    if oid is None or rpid is None:
        print("没有oid rpid？")
        return
    key = f"RP-{oid}-{rpid}"
    oidStr = str(oid)
    rpidStr = str(rpid)

    if _checkRowExsit(key,'comments','key'):
        return
    
      # key oid    , bvid  , title  , rpid      , msg     , ctime  , deltime  , flag  ,   json     
    cursor.execute('''
        INSERT OR IGNORE INTO comments (key, oid    , bvid  , title  , rpid      , msg     , ctime  , deltime  , flag  ,   json  ) VALUES (?,?,?,?,?,?,?,?,?,?)
    ''',(key,oidStr,item.get('bvid'),item.get('title'),rpidStr,item.get('msg'),item.get('ctime'),item.get('delTime'),item.get('flag'),json.dumps(item, indent=4,ensure_ascii=False),))
    
    conn.commit()
    
def updateHistoryLatestCommentTime(oid,timeSec):
    cursor.execute('''
        UPDATE histories SET newest_cmt_time = ?  WHERE oid = ? and (newest_cmt_time  < ? or newest_cmt_time is NULL)
    ''',
    (timeSec,str(oid),timeSec)
    )
    conn.commit()

def updateCommentFlag(oid,rpid,flag):
    if oid is None or rpid is None:
        return
    key = f"RP-{oid}-{rpid}"
    cursor.execute('''
        UPDATE comments SET flag = ?  WHERE key = ? and (flag != ? or flag is NULL)
    ''',
    (flag,key,flag)
    )
    conn.commit()


def updateQueryCommentCtx(time_at,oid,pageIdx):
    if time_at is not None:
        setConfig('currentQueryTime',intV= time_at)
    if oid is not None:
        setConfig('currentQueryOid',strV= str(oid))
    if pageIdx is not None:
        setConfig('currentQueryPageNo',intV=pageIdx)


def getQueryHistoryCtx():
    return getConfig('QueryHistoryTimeNear'),getConfig('QueryHistoryTimeFar')


def updateQueryHistoryCtx(timeNear,timeFar):
    if timeNear is not None:
        setConfig('QueryHistoryTimeNear',intV= timeNear)
    if timeFar is not None:
        setConfig('QueryHistoryTimeFar',intV= timeFar)
    

def getCurrentQueryProgress():
    return getConfig('currentQueryTime'),getConfig('currentQueryOid'),getConfig('currentQueryPageNo')

def getUnqueryHistory(CUNT=15):
    ct,oid,viewAt = getCurrentQueryProgress()

    cursor.execute('SELECT * from "histories" where view_at >= ? and (newest_cmt_time is   null or newest_cmt_time == 0)   order by view_at desc  limit ?',(viewAt,CUNT) )

    rows = cursor.fetchall()
    r = []
    for itm in rows:
        mp = dict(itm)
        del mp['json']
        r.append(mp)
    return r 

def insertHistoryFromConfig():
    HISTORY = config.getJsonConfig('history')
    config.saveJsonConfig(HISTORY,'history')
    hisList = HISTORY['list']
    printD("history count",len(hisList))
  
    for i in hisList:
        insertHistoryItem(i)
    
   

    printD("XX",getHistoryCount())
    
def insertCommentsFromConfig():
    clist = config.getJsonConfig('comments2')
    cmtlist = clist['list']
    for i in cmtlist:
        insertCommentItem(i)

def updateHistoryLatestCmtTimeFromConfig():
    mp = config.getJsonConfig('LstCmtTimeForOid')
    
    for oid,time in mp.items():
        updateHistoryLatestCommentTime(oid,time)




def getHistoryCount():
    cursor.execute('SELECT count(1) as c from histories ')
    row = cursor.fetchone()
    return  dict(row).get("c")


def getHistoryTimeRange():
    cursor.execute(f"SELECT view_at from histories order by view_at desc limit 1")
    row = cursor.fetchone()
    near = None
    if row is not None:
        near = dict(row).get("view_at")

    cursor.execute(f"SELECT view_at from histories order by view_at asc  limit 1")
    row = cursor.fetchone()
    far = None
    if row is not None:
        far = dict(row).get("view_at")
    return near,far

def setQueryCtrFromCfg():
    query_progress = config.getJsonConfig('query_progress')
    timeAt = query_progress.get('LastTimeAt')
    page = query_progress.get('page')
    oid = query_progress.get('oid')


    updateQueryCommentCtx(timeAt,oid,page)


def setQueryHistoryFromCfg():
    query_progress = config.getJsonConfig('history')
    nearTime = query_progress.get('LastViewTimeSec')
    farTime = query_progress.get('QueryTime')


    updateQueryHistoryCtx(nearTime,farTime)





 

if __name__ == '__main__':
 
     initDB()
    #  printD(getUnqueryHistory())
    #  setConfig("TESTb",None,12)
     insertHistoryFromConfig()
     insertCommentsFromConfig()
     updateHistoryLatestCmtTimeFromConfig()

     setQueryCtrFromCfg()

    #  printD(getCurrentQueryProgress())

     setQueryHistoryFromCfg()

     printD(getQueryHistoryCtx())

     printD(getHistoryCount())





     closeDb()
     exit(1)
  
  

    



