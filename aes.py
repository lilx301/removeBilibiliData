import os
import sys
sys.path.insert(0, './pylib')
from Crypto.Cipher import AES
import hashlib
import base64


class AEScoder():
    def __init__(self,key):
        md = hashlib.sha256();
        md.update(key.encode('utf-8'))                   #制定需要加密的字符串
        realkey = md.hexdigest()[:32]
        self.__key = realkey.encode("utf-8");
    # AES加密
    def encrypt(self,data):
        BS = 16
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        cipher = AES.new(self.__key, AES.MODE_ECB)
        encrData = cipher.encrypt(pad(data).encode('utf-8'))
        encrData = base64.b64encode(encrData)
        return encrData.decode('utf-8')
    # AES解密
    def decrypt(self,encrData):
        encrData = base64.b64decode(encrData)
        # unpad = lambda s: s[0:-s[len(s)-1]]
        unpad = lambda s: s[0:-s[-1]]
        cipher = AES.new(self.__key, AES.MODE_ECB)
        decrData = unpad(cipher.decrypt(encrData))
        return decrData.decode('utf-8')

if __name__ == "__main__":
    t = AEScoder("12");
    e = t.encrypt("123");
    print (e);
    p = t.decrypt(e);
    print ("\n",p);
    
    enc=AEScoder(os.getenv('CFGKEY'))
    cfgStr = open(  "cfg.json").read();
    cfgEnc = enc.encrypt(cfgStr)

    print("\n\n\n----------------------------------")
    print("根据 cfg.json 明文生成 cfgA.json.en\n 如果以此为准，那么将cfgA.json.enc 覆盖 cfg.json.enc")
    text_file = open("cfgA.json.enc", "w")
    text_file.write(cfgEnc);
    text_file.close()

    print("\n\n\n----------------------------------")
    print("根据 cfg.json.enc 远端密文生成 cfgA.json\n 如果以此为准，那么将cfgA.json 覆盖 cfg.json")

    tmp2 = open(  "cfg.json.enc").read();
    cfgDec = enc.decrypt(tmp2)

    text_file = open("cfgA.json", "w")
    text_file.write(cfgDec);
    text_file.close()





    