
import config
import gzip
import hashlib

def md5(data):
    return hashlib.md5(data).hexdigest()

# config.getJsonConfig('cfg')
# config.getJsonConfig('comments')
# config.getJsonConfig('comments2')
# config.getJsonConfig('query_progress')


s = '12412313124123131241231312412313124123131241231312412313124123131241231312412313';

print(md5(gzip.compress(s.encode('utf-8'),mtime=0,compresslevel=9)))