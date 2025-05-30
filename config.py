import re
import time
import sys
import os
import random

sys.path.insert(0, os.path.abspath("pylib"))
import requests 

import base64
import json
from aes import AEScoder 
 
def saveJsonConfig(jsonOBJ,name):
    jsonStrNew = json.dumps(jsonOBJ, indent=4,ensure_ascii=False)

    KEY=os.getenv('CFGKEY')
    if KEY is None:
        print("No CFGKEY")
        exit(1)

    encFile = f"data/{name}.json.enc"
    enc=AEScoder(os.getenv('CFGKEY'))
    jsonEncStr = enc.encrypt(jsonStrNew)
    try:
        with open(encFile,'w') as f:
            f.write(jsonEncStr)

    except Exception as e :
        print(e)

    if os.getenv('DEBUG') is not None and os.getenv('DEBUG') == '1':
        with open(f"data/{name}.json",'w') as f:
            f.write(jsonStrNew)
     

def getJsonConfig(name,NonIfNotExist=False):
    encStr = '{}'
    encFile = f"data/{name}.json.enc"
    KEY=os.getenv('CFGKEY')
    if KEY is None:
        print("No CFGKEY")
        exit(1)
    try:
        with open(encFile) as f:
            encStr = f.read()
        enc=AEScoder(os.getenv('CFGKEY'))
        jstring = enc.decrypt(encStr)
        jsonOBJ = json.loads(jstring)
        jsonOBJ['_NAME_CFG'] = name
        return jsonOBJ
    except Exception as e :
        if NonIfNotExist:
            return None
        print('读取配置错误，创建一个空配置',name,e)
        return {}
    



 

if __name__ == '__main__':
    ob = getJsonConfig('cfg')
    enc=AEScoder(os.getenv('CFGKEY'))
    try:
        with open(  "data/cfg.json") as f:
            cfgStr = f.read()
            cfgEnc = enc.encrypt(cfgStr)
            print("\n\n\n----------------------------------")
            print("根据 cfg.json 明文生成 cfgA.json.en\n 如果以此为准，那么将cfgA.json.enc 覆盖 cfg.json.enc")
            text_file = open("cfgA.json.enc", "w")
            text_file.write(cfgEnc);
            text_file.close()
    except Exception as e :
        print('err')
    finally:
        print('----------------------------')
    

    

    print("\n\n\n----------------------------------")
    print("根据 cfg.json.enc 远端密文生成 cfgA.json\n 如果以此为准，那么将cfgA.json 覆盖 cfg.json")

    tmp2 = open(  "data/cfg.json.enc").read();
    cfgDec = enc.decrypt(tmp2)

    text_file = open("data/cfgA.json", "w")
    text_file.write(cfgDec);
    text_file.close()

