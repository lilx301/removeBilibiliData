import re
import time
import sys
import os
import json
sys.path.insert(0, os.path.abspath("pylib"))

import db
from debug import printD ,isDebug

import config

import notice
    
     

def getCurrentState():
    historyCount = db.getHistoryCount( )
    commentCount = db.getAllCommentCount( )
    delCount = db.getDeleteCommentCount( )
    printD("当前历史记录数量:", historyCount)
    printD("当前评论数量:", commentCount)

    return  {
        'historyCount': historyCount,
        'commentCount': commentCount,
        'delCount': delCount,
        'now': int(time.time())
    }

    pass

def  getNewDetail(time):
    arr  = db.getCommentsAfterTime(time)
    return arr

    


def mainfunc():

    # importRepliesViaAICUData()
    # testGetRep()

    taskType = sys.argv[1] if len(sys.argv) > 1 else None

    if taskType is None :
        
        print("没有指定任务类型")
        print("请使用 python state.py <taskType> 来指定任务类型")
        print("taskType 0: 保存当前状态到 tmpdata.json")
        print("taskType 1: 发送通知 变化")

        return
    elif taskType == '1':
        print("保存状态")
        cfg0 = getCurrentState()
        printD("当前状态:", cfg0)
        config.saveJsonConfig(cfg0, "tmpdata")

    elif taskType == '2':
        print("检查状态变更，并通知")
        cfg0 = config.getJsonConfig("tmpdata")
        cfg2 = getCurrentState()

        historyCount0 = cfg0.get('historyCount', -1)
        historyCount1 = cfg2.get('historyCount', -1)

        commentCount0 = cfg0.get('commentCount', -1)
        commentCount1 = cfg2.get('commentCount', -1)

        delCount0 = cfg0.get('delCount',-1)
        delCount1 = cfg2.get('delCount',-1)


        

        if historyCount0 == historyCount1 and commentCount0 == commentCount1 and delCount0 == delCount1:
            print("没有变化")
            if not isDebug():
                return

        msg = f'''
浏览记录: + {'None' if historyCount0 == -1 or historyCount1 == -1 else historyCount1 - historyCount0 : 5d}
评论数量: + {'None' if commentCount0 == -1 or commentCount1 == -1 else commentCount1 - commentCount0 : 5d}
删除数量: - {'None' if delCount0 == -1 or delCount1 == -1 else delCount1 - delCount0: 5d}
        '''
        print(msg)
        notice.sendBarkMsg(msg)

        arrCmt = getNewDetail(cfg0.get('now', int(time.time())-60))
        if len(arrCmt) > 0:

            
            arrCmt1 = [cmt for cmt in arrCmt if cmt['flag'] == 1]  
            arrCmt0 = [cmt for cmt in arrCmt if cmt['flag'] == 0 or cmt['flag'] is None]
            msgDetail = f'新评论：{len(arrCmt0)}\n'
            for cmt in arrCmt0:
                msgDetail += f"[{cmt['title']}]\n\tR:{cmt['msg']}\n\n"



            msgDetail += f'\n--------\n删除评论：{len(arrCmt1)}\n'
            for cmt in arrCmt1:
                # printD("新评论:", cmt)
                msgDetail += f"[{cmt['title']}]\n\tR:{cmt['msg']}\n\n"

            notice.sendTgMsg(msgDetail)

        
   

if __name__ == '__main__':
    
    try:
        db.initDB()
        mainfunc()

        
    except KeyboardInterrupt as e:
        print(e)
    else:
        print("EEE")
    finally:
        print("XX")
        db.closeDb()



    



