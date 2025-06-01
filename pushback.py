
import sys
import os
import subprocess
sys.path.insert(0, os.path.abspath("pylib"))
import db

def _pushback(msg=None):
    subprocess.run(('sh','cipushback.sh', f'{msg}'))
    

def pushback(msg=None):
    # 关闭数据库，生成文件，然后pushback
    if not db.isDbConnected():
        
        print("数据库未连接？没必要执行pushback")
        return
    

    db.closeDb()
    

    try:
        _pushback()
    except Exception as e:
        print("Pushback failed:", e)
    finally:
        # 重新打开数据库,方便后续的
        db.initDB()



if __name__ == "__main__":
    _pushback("Test pushback message")