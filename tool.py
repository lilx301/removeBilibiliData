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
beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
def timeStamp2Str(timestamp: int) -> str:
    if timestamp is None:
        return ''
    dt = datetime.datetime.fromtimestamp(timestamp, tz=beijing_tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S")




def ymd2Stamp(date_str: str, fmt: str = "%Y-%m-%d", ms: bool = False) -> int:
    
    t = time.strptime(date_str, fmt)
    timestamp = calendar.timegm(t) - 8 * 3600
    return int(timestamp * 1000) if ms else int(timestamp)

def  getObjWithKeyPath(obj,keypath):
    if obj is None or keypath is None:
        return None
    arr = keypath.split('.')
    sitem = obj
    for name in arr :
        sitem = sitem.get(name)
        if sitem is None:
            return None
    
    return sitem