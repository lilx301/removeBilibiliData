import os
import sys
sys.path.insert(0, './pylib')
from Crypto.Cipher import AES
import hashlib
import base64
from Crypto.Util.Padding import pad
from Crypto.Util.Padding import unpad


class AEScoder():
    def __init__(self,key,israw=0):
        realkey = None
        
        if israw:
            realkey = key
        else: 
            md = hashlib.sha256();  
            md.update(key.encode('utf-8'))                   #制定需要加密的字符串
            realkey = md.hexdigest()[:32]
        self.__key = realkey.encode("utf-8")
        
    # AES加密
    def encrypt(self,data):
        BS = 16
        pad = lambda s: s + (BS - len(s.encode('utf-8')) % BS) * chr(BS - len(s.encode('utf-8')) % BS)
        cipher = AES.new(self.__key, AES.MODE_ECB)
        encrData = cipher.encrypt(pad(data).encode('utf-8'))
        encrData = base64.b64encode(encrData)
        return encrData.decode('utf-8')
    
    def encryptBin(self, data: bytes) -> bytes:
        BS = 16
        cipher = AES.new(self.__key, AES.MODE_ECB)
        padded_data = pad(data, BS)
        return cipher.encrypt(padded_data)
    def decryptBin(self, data: bytes) -> bytes:
        cipher = AES.new(self.__key, AES.MODE_ECB)
        decrData = unpad(cipher.decrypt(data),16)
        return decrData
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

    


 





    
