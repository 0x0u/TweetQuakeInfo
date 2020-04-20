# TweetQuakeInfo
気象庁の「震源・震度に関する情報」をツイートするやつ

Follow Me!! => [@v0x0o](https://twitter.com/v0x0o)

## Directory
* `gae/` 
    * GoogleAppEngine
* `cf/` 
    * CloudFunctions 


## How it works

* 気象庁から気象庁防災情報XMLフォーマット形式電文がAppEngineにpushされる
* 「震源・震度に関する情報」がpushされた場合パラメーターにURLを含めCloudFunctionsにgetする
* URLからXMLをパースしTweetする

![](https://user-images.githubusercontent.com/34241526/79744396-398ee380-8341-11ea-9252-cb4ff59d4956.png)
