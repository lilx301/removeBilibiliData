import re
import time
import sys
import os

sys.path.insert(0, os.path.abspath("pylib"))

import db
from debug import printD 

import config
import urllib.parse

from aes  import AEScoder
import requests
from tool import timeStamp2Str
import json
import random

TGBOT = config.getJsonConfig('cfg').get('TGBOT')
BARKURL = config.getJsonConfig('cfg').get('BARK_URL')
BARKKEY = config.getJsonConfig('cfg').get('BARK_KEY')

"""
全局 5% 概率门控：进程生命周期内固定
"""
SHOULD_SEND_NOTICE = True #(random.random() < 0.05)



def sendTgMsg(msg):
    if not SHOULD_SEND_NOTICE:
        printD("跳过发送(5% 概率门控):", msg)
        return
    if TGBOT is not None:
        requests.post(TGBOT,data={
            'text':f"{msg}\n{timeStamp2Str(time.time())}",
         })
            
    else:
        print("没有配置 TGBOT")


def sendBarkMsg(msg):
    if not SHOULD_SEND_NOTICE:
        printD("跳过发送(5% 概率门控):", msg)
        return
    if BARKURL is not None and BARKKEY is not None:
        ENC = AEScoder(BARKKEY,israw=1 )
        
        msg=f"{msg}\n{timeStamp2Str(time.time())}"

        body = {
            "body":msg,
            "sound": "birdsong"
        }        

        msgE = ENC.encrypt(json.dumps(body))
        printD(msgE)
        

        requests.post(BARKURL,data={
            'ciphertext':msgE,
            'sound':"birdsong"
        })
def sendMsg(msg):
    printD("发送通知:", msg)
    
    # sendBarkMsg(msg)
    sendTgMsg(msg)
    
        

    
    
    
    print("通知变化")
    pass
def mainfunc():

    # importRepliesViaAICUData()
    # testGetRep()

    sendMsg("测试通知功能")

    
         
   

if __name__ == '__main__':
    
    try:

        mainfunc()
    except KeyboardInterrupt as e:
        print(e)
    else:
        print("EEE")
    finally:
        print("XX")



    



