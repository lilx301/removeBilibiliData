
import config
import gzip
import hashlib
import db 

def md5(data):
    return hashlib.md5(data).hexdigest()

# config.getJsonConfig('cfg')
# config.getJsonConfig('comments')
# config.getJsonConfig('comments2')
# config.getJsonConfig('query_progress')




s = '12412313124123131241231312412313124123131241231312412313124123131241231312412313';

print(f"{333:04d}",int('0000123'))

print("2025-02-21 12:31:51"[0:-5])


db.initDB()  # 初始化数据库连接
ta,preQueryOid, initPage = db.getCurrentQueryProgress()
print(ta,preQueryOid, initPage)

db.closeDb()