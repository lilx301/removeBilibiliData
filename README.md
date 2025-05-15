# deleteFans
Bilibili移除自己的粉丝


本项目主要是觉得你粉丝数量太多,或者被恶意刷粉,进行的移除粉丝操作

经测试 一天只能移除500个粉丝 超过500个会提示 {'code': -509, 'message': '请求过于频繁，请稍后再试', 'ttl': 1}




```
 pip3 install -r requirements.txt --target=./pylib
```

在github secret 中设置 COOKIE64=Base64(bilibil cookie)


#TODO
刷新cookie，果然事情没这么简单。  


[接口这里](https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/cookie_refresh.md)

[这里](https://github.com/SocialSisterYi/bilibili-API-collect/issues/524)

  