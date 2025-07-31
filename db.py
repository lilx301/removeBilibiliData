import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))
import config
from debug import printD
import json
import tool 
import gzip
import time
from aes import AEScoder 
ENC =AEScoder(os.getenv('CFGKEY'))
conn = None
cursor = None

import hashlib
def isDbConnected():
    return conn is not None and cursor is not None 

def closeDb():
    global cursor, conn
    if conn is not None:
        cursor.close()
        conn.close()
        cursor = None
        conn = None
    encDb()
    setWorkingFlag(False)


def setWorkingFlag(flg:bool):
    with open("data/flg.txt",'w') as f:
        f.write('1' if flg else '0')

def checkOtherInstanceWorking():
    try:
        with open("data/flg.txt",'r') as f:
            x = f.read()
            return x == '1'
    except Exception as e:
        pass
    

    return False

def initDB():
    global conn
    global cursor
    if conn == None:

        if checkOtherInstanceWorking():
            print("检测到其他实例正在运行，无法初始化数据库 [data/flg.txt == 1]   退出")
            exit(1)
        
        setWorkingFlag(True)

        decDb()
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
        
        # ex2 表示访问时间，用 ;分割
        # ex1 表示是否请求过，评论 NULL 或者 0 表示未请求过，1 已经请求了，
        # 历史记录重新更新，会重置
        
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
         # ex1 表示来源，是否是AICU
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
            ex1 TEXT,
            ex2 TEXT,
            ex3 TEXT,
            json TEXT  ,
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


def getNewestAICUCommentCtime():
    cursor.execute("SELECT ctime FROM comments WHERE ex1 = 'AICU' ORDER BY ctime DESC LIMIT 1")
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(row).get('ctime')   

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
                    SELECT * from "{tableName}" where {keyname} = ? limit 1
                   """,
                   (key,)
                   )
    exsist = cursor.fetchone()
    if exsist is not None:
        return True,dict(exsist)
    return False,None


def insertHistoryItem(item):
    '''
     {
            "oid": 1111,
            "epid": 0,
            "bvid": "BV133",
            "page": 1,
            "cid": 122,
            "part": "标题 or xxx.mp4",
            "title":"标题",
            "business": "archive",
            "dt": 1,
            "view_at": 174000000
        },
    '''

    printD(f'{item.get("title")}       {item.get("part")}')

    oid = item.get('oid')
    if oid is None:
        print("没有oid？？")
        return
    
    oidStr = str(oid)

    exist,dbObj = _checkRowExsit(oidStr,'histories','oid')

    if exist:
        printD("历史记录已存在，跳过插入",oidStr)
        # 存在就 更新 时间
        updateHistoryViewTime(oidStr,item.get('view_at'),dbObj)

        return
    
    
    #  oid  bvid title, business view_at newest_cmt_time json          
    jsonstr = None #json.dumps(item, indent=4,ensure_ascii=False)
    cursor.execute('''
        INSERT OR IGNORE INTO histories (oid , bvid , title, business ,view_at ,newest_cmt_time , json) VALUES (?,?,?,?,?,?,?)
    ''',(oidStr,item.get('bvid'),item.get('title'),item.get('business'),item.get('view_at'),item.get('newest_cmt_time'),jsonstr,))
    
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

    exsist, _ = _checkRowExsit(key,'comments','key')
    if exsist:
        printD("----------------------评论已存在，跳过插入")
        return
    
      # key oid    , bvid  , title  , rpid      , msg     , ctime  , deltime  , flag  ,   json  

    jsonStr = None # item.get('json') if item.get('json') is not None else json.dumps(item, indent=4,ensure_ascii=False)   
    cursor.execute('''
        INSERT OR IGNORE INTO comments (key, oid    , bvid  , title  , rpid      , msg     , ctime  , deltime  , flag  , ex1 ,ex2,ex3,  json  ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''',(key,oidStr,item.get('bvid'),None ,rpidStr,item.get('msg'),item.get('ctime'),item.get('delTime'),item.get('flag'),
         item.get('ex1'),item.get('ex2'),item.get('ex3'),
         jsonStr
         ))
    
    conn.commit()

def updateHistoryViewTime(oid,viewat,oldObj):
    viewTimeList = None
    if oldObj is not None:
        if oldObj.get('ex2') is not None: 
            viewTimeList = f"{oldObj.get('ex2') };{viewat}" 
        else:
            viewTimeList = f"{oldObj.get('view_at')};{viewat}"
    cursor.execute('''
        UPDATE histories SET view_at = ? ,ex2 = ? ,ex1 = NULL  WHERE oid = ? and ((view_at  < ? or view_at is NULL) or ex1 is not NULL)
    ''',
    (viewat,viewTimeList,str(oid),viewat)
    )
    conn.commit()
    # TODO: 这里需要更新最新评论时间
    
def updateHistoryLatestCommentTime(oid,timeSec):
    cursor.execute('''
        UPDATE histories SET newest_cmt_time = ? , ex1 = '1' WHERE oid = ? and ((newest_cmt_time  < ? or newest_cmt_time is NULL) or ex1 is null)
    ''',
    (timeSec,str(oid),timeSec)
    )
    conn.commit()

def updateCommentFlag(oid,rpid,flag):
    
    if oid is None or rpid is None:
        return
    key = f"RP-{oid}-{rpid}"
    printD('updateCommentFlag',oid,rpid,flag,key)
    if flag == 1:

        cursor.execute('''
            UPDATE "comments" SET flag = ? , deltime = ?  WHERE key = ?  
        ''',
        (flag,int(time.time()),key)
        )
    else:
        cursor.execute('''
            UPDATE "comments" SET flag = ?  WHERE key = ?  
        ''',
        (flag,key)
        )

    
    if flag == 1:
        printD('标记为删除')

    printD('row effect:',cursor.rowcount)

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




def getUnQueryHistoryCount():
    cursor.execute('SELECT count(1) as c from histories where  ex1 is null limit 1')
    row = cursor.fetchone()
    return  dict(row).get("c")

def getUnqueryHistory(CUNT=100):
    # viewAt,oid,pageNo = getCurrentQueryProgress()
    cursor.execute('SELECT * from "histories" where  ex1 is null    order by view_at asc   limit ?',(CUNT,) )

    rows = cursor.fetchall()
    r = []
    for itm in rows:
        mp = dict(itm)
        del mp['json']
        r.append(mp)
    return r 


def getUndeletedCommentsCount(timeStamp):
    
    cursor.execute('SELECT count(1) as c from "comments" where ( flag is null or flag = 0  ) and ctime < ?', (timeStamp,))
    row = cursor.fetchone()
    return dict(row).get("c")

def getUndeletedComments(timeStamp,COUNT = 100):
    printD('getUndeletedComments',timeStamp)
    cursor.execute('SELECT * from "comments" where ( flag is null or flag = 0  ) and ctime < ? order by ctime asc limit ? ', (timeStamp, COUNT))
    rows = cursor.fetchall()
    if rows is not None:
        r = []
        for row in rows:
            r.append(dict(row))
        
        return r 
        
    return []



def getAllCommentCount():
    cursor.execute('SELECT count(1) as c from comments  limit 1')
    row = cursor.fetchone()
    return dict(row).get("c")

def getDeleteCommentCount():
    cursor.execute('SELECT count(1) as c from comments where flag is not null and  flag != 0 limit 1')
    row = cursor.fetchone()
    return dict(row).get("c")

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





def decDb():
    try:
        combineSliceDb()
    except Exception as e:
        pass



def encDb():
    try:
        sliceDbFile()
    except Exception as e:
        printD("切片失败",e)





def combineSliceDb():
   
    dgst = hashlib.new('sha256')
    COUNT = 0
    with open(f"data/db/biliCount", 'r') as f:
        COUNT = int(f.read())
    
    # data/bilidata.db 清空
    with open('data/bilidata.db', 'w') as f:
        pass  # 或 f.write('')
    with open('data/bilidata.db', 'ab') as out_file:
        for i in range(0, COUNT):
            with open(dbfileNameForIdx(i), 'rb') as in_file:
                chunkOri = in_file.read()
                dgst.update(chunkOri)
                gzipped_chunk = ENC.decryptBin(chunkOri)
                # 解压缩
                chunk = gzip.decompress(gzipped_chunk)
                # 写入到输出文件    
                out_file.write(chunk)


    # 检查完整性
    sha = dgst.hexdigest()
    printD("合并完成",COUNT,"个文件",sha)

    with open(f"data/db/biliHash", 'r') as f:
        hashOri = f.read().strip()
        if sha != hashOri:
            print("\n\n\n-- 数据库完整性校验失败 --\n\n\n")
            exit(1)
            # raise RuntimeError("数据库完整性校验失败，切片文件可能损坏，请重新切片")
        else:
            print("\n\n\n-- 数据库完整性校验通过 ok --\n\n\n")


def dbfileNameForIdx(idx):
    return f"data/db/bili.part_{idx:07d}"

def sliceDbFile():

    dgst = hashlib.new('sha256')

    
    # sqlite 页 4096 尽量减少 大文件变动
    chunk_size = 4096 * 8
    with open('data/bilidata.db','rb') as f:
        i = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            gzipped_chunk = gzip.compress(chunk, mtime=0, compresslevel=5)
            binEnc = ENC.encryptBin(gzipped_chunk)
            dgst.update(binEnc)
            with open(dbfileNameForIdx(i), 'wb') as out_file:
                out_file.write(binEnc)
            i += 1
        with open(f"data/db/biliCount", 'w') as out_file:
            out_file.write(str(i))

        with open(f"data/db/biliHash", 'w') as out_file:
            dgstResult = dgst.hexdigest()
            out_file.write(dgstResult)
            print("切片完成",i,"个文件",dgstResult)
        # 删除需要大于 count的文件

        folder_path = 'data/db'  # 替换为你的目标文件夹路径

        for filename in os.listdir(folder_path):
            if filename.startswith('bili.part_'):
                countF = int(filename.split('part_')[1])
                file_path = os.path.join(folder_path, filename)
                if countF >= i:
                    printD('del',file_path,countF)
                    os.remove(file_path)
                    continue

                
                # if os.path.isfile(file_path):
                    # os.remove(file_path)
                    # print(f'Deleted: {file_path}')

        
    


def exportComent(all = True):
    cursor.execute(f"""
        SELECT c.msg, 
               COALESCE(h.title, c.title) as title, 
               c.ctime
        FROM comments c
        LEFT JOIN histories h ON c.oid = h.oid
        {'' if all else 'WHERE c.flag IS NULL OR c.flag = 0'}
        ORDER BY c.ctime DESC
    """)
    clst  = cursor.fetchall()
    arr = []
    for itm in clst:
        mp = dict(itm)
        mp['ctime'] = tool.timeStamp2Str(mp.get('ctime'))
        arr.append(mp)

    arr2 = []
    hisCount = 0
    if all :
        cursor.execute("select bvid ,title,view_at from histories  order by view_at desc  ")
        hlist  = cursor.fetchall()
        
        for itm in hlist:
            mp = dict(itm)
            mp['ctime'] = tool.timeStamp2Str(mp.get('view_at'))
            arr2.append(mp)
        hisCount = len(hlist)
    else:
        cursor.execute("select count(1) from histories   ")
        row  = cursor.fetchone()
        hisCount = dict(row).get('count(1)')


    cursor.execute("select count(1) from comments   ")
    row  = cursor.fetchone()
    countAllCmt = dict(row).get('count(1)')

    print("历史记录数量",hisCount)
    print(f"历史评论数量 {len(arr)} / {countAllCmt}")
    jsonstr = json.dumps({"list":arr,'history':arr2,'a_rep':len(arr),'a_his':hisCount},indent=4,ensure_ascii=False)
    with open('data/export.json','w') as f:
        f.write(jsonstr)

def getCommentsCountByType(type):

    cursor.execute(f'SELECT count(1) as c FROM comments WHERE ex1 = "{type}"')

    return dict(cursor.fetchone()).get('c', 0)

def test():

    # cursor.execute("UPDATE comments SET title = null ")
    # conn.commit()
    pass 

def getCommentsAfterTime(timeSec):
    printD('getCommentsAfterTime', timeSec)
    cursor.execute('SELECT flag, deltime, ctime,title,msg from "comments" where ctime > ? or deltime > ? order by ctime asc', (timeSec, timeSec  ))
    rows = cursor.fetchall()
    if rows is not None:
        r = []
        for row in rows:
            r.append(dict(row))
        
        return r
    return []

if __name__ == '__main__':
 
     initDB()
     exportComent(False)

     printD(getUnQueryHistoryCount())

     test()

    #  printD(getUnqueryHistory())
    #  setConfig("TESTb",None,12)
    #  insertHistoryFromConfig()
    #  insertCommentsFromConfig()
    #  updateHistoryLatestCmtTimeFromConfig()

    #  setQueryCtrFromCfg()

    # #  printD(getCurrentQueryProgress())

    #  setQueryHistoryFromCfg()

    #  printD(getQueryHistoryCtx())

    #  printD(getHistoryCount())


    #  printD(getUnqueryHistory())

    #  printD('XBd',getUndeletedComments()[1])

  






    #  cursor.execute("vacuum;")
    #  conn.commit()
     closeDb()
     exit(1)
  
  

    



