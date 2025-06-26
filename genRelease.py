import re
import time
import sys
import os

from aes import AEScoder
import gzip
import tool
ENCTOOL =AEScoder(os.getenv('CFGKEY'))
def decryptData():
    try:
        with open('data/sqlite_backup.gz.en','rb') as f:
            bf = f.read()
            bfD = ENCTOOL.decryptBin(bf)
            bf2 = gzip.decompress(bfD)
            
            with open('data/tmpdata_sqlite_backup.db','wb') as outf:
                outf.write(bf2)

    except Exception as e:
        print(e)
        pass


if __name__ == '__main__':
    NeedGenReleaseFile = True
    DAY = 17
    try:
        preDate = None
        with open('data/releasetime.txt','r') as f:
            preDate = f.read()
        
        tpre = tool.ymd2Stamp(preDate,fmt = "%Y-%m-%d %H:%M:%S")
        tnow = int(time.time())
        print(f'【{DAY}】 距离上次 {(tnow-tpre)/3600:.2f}h    {(tnow-tpre)/86400:.1f}d ')
        if tnow - tpre < DAY * 86400:
            NeedGenReleaseFile = False
        
        
        
    except Exception as e:
        print(e)
        pass
    finally:
        print(f"是否生成Release ? { '✅' if NeedGenReleaseFile else '❌'}")
    
    
    if NeedGenReleaseFile:
        with open('data/bilidata.db','rb') as f:
            bf = f.read()
            gzbf = gzip.compress(bf,mtime=0)
            encBf = ENCTOOL.encryptBin(gzbf)
            with open('data/sqlite_backup.gz.en','wb') as outf :
                outf.write(encBf)
            
            t = int(time.time())
            
            with open('data/releasetime.txt','w') as outf:
                outf.write(tool.timeStamp2Str(t))

    
   



    



