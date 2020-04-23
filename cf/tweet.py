import os
import re
import tweepy
import requests
import xmltodict
from io import BytesIO
from datetime import datetime
from bs4 import BeautifulSoup


LINE_NOTIFY_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN")

TWITTER_CONSUMER_KEY = os.environ.get("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_KEY = os.environ.get("TWITTER_ACCESS_KEY")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")
auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_KEY, TWITTER_ACCESS_SECRET)
api = tweepy.API(auth)


def send_message(message):
    url = "https://notify-api.line.me/api/notify"
    payload = {"message": message}
    headers = {"Authorization": "Bearer " + LINE_NOTIFY_TOKEN}
    r = requests.post(url, data=payload, headers=headers)
    return r.status_code


def tweet(tweet_text, tweet_id=None, tweet_img=None):
    if tweet_id:
        return api.update_status(status=tweet_text, in_reply_to_status_id=tweet_id).id
    else:
        result_img = api.media_upload(filename="eew.png", file=tweet_img)
        return api.update_status(status=tweet_text, media_ids=[result_img.media_id]).id


def get_eew_img():
    url = "https://www.jma.go.jp/jp/quake"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    img_url = url + soup.find("img", usemap="#quakemap").get("src").replace(".", "", 1)
    img = requests.get(img_url)
    img_obj = BytesIO(img.content)
    return img_obj


def parse_xml(url):
    r = requests.get(url)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "lxml")

    data_dic = xmltodict.parse(r.text)

    # 発表かどうか
    info_type = data_dic["Report"]["Head"]["InfoType"]
    if info_type != "発表":
        exit()

    # 国内発生かどうか
    datum = data_dic["Report"]["Body"]["Earthquake"]["Hypocenter"]["Area"]["jmx_eb:Coordinate"].get("@datum")
    if datum is None:
        exit()

    # 発生時刻
    origin_time = data_dic["Report"]["Body"]["Earthquake"]["OriginTime"]
    origin_time_tmp = datetime.strptime(origin_time, "%Y-%m-%dT%H:%M:00+09:00")
    origin_time_text = origin_time_tmp.strftime("%Y年%-m月%-d日 %-H時%-M分ごろ")

    # 震源地
    epicenter_text = data_dic["Report"]["Body"]["Earthquake"]["Hypocenter"]["Area"]["Name"]

    # 最大震度
    maxint = data_dic["Report"]["Body"]["Intensity"]["Observation"]["MaxInt"]
    maxint_text = maxint.replace("-", "弱").replace("+", "強")

    # マグニチュード
    magnitude_text = data_dic["Report"]["Body"]["Earthquake"]["jmx_eb:Magnitude"]["#text"]

    # 座標
    hypocenter = data_dic["Report"]["Body"]["Earthquake"]["Hypocenter"]["Area"]
    description = hypocenter["jmx_eb:Coordinate"]["@description"]
    if description == "震源要素不明":
        lat_text = "不明"
        lon_text = "不明"
        depth_text = "不明"
    else:
        coor_tmp = hypocenter["jmx_eb:Coordinate"]["#text"]
        coor = re.findall("[+-](\d*[.,]?\d*)", coor_tmp)
        lat_text = "N" + coor[0]
        lon_text = "E" + coor[1]
        depth = int(coor[2]) / 1000
        if depth <= 5:
            depth_text = "ごく浅い"
        elif depth >= 700:
            depth_text = "700km以上"
        else:
            depth_text = str(depth) + "km"

    tweet_text = "【メンテナンス】\n発生時刻: {}\n震源地: {}\n最大震度: {}\nマグニチュード: M{}\n深さ: {}\n座標: {}/{}".format(origin_time_text, epicenter_text, maxint_text, magnitude_text, depth_text, lat_text, lon_text)
    tweet_img = get_eew_img()
    tweet_id = tweet(tweet_text=tweet_text, tweet_img=tweet_img)

    city_data_dic = {
        "si1": [],
        "si2": [],
        "si3": [],
        "si4": [],
        "si5m": [],
        "si5p": [],
        "si6m": [],
        "si6p": [],
        "si7": []
    }

    cities = soup.find_all("city")
    for i in cities:
        name = i.find("name").text
        maxint = i.find("maxint").text
        if maxint == "1":
            city_data_dic["si1"].append(name)
        elif maxint == "2":
            city_data_dic["si2"].append(name)
        elif maxint == "3":
            city_data_dic["si3"].append(name)
        elif maxint == "4":
            city_data_dic["si4"].append(name)
        elif maxint == "5-":
            city_data_dic["si5m"].append(name)
        elif maxint == "5+":
            city_data_dic["si5p"].append(name)
        elif maxint == "6-":
            city_data_dic["si6m"].append(name)
        elif maxint == "6+":
            city_data_dic["si6p"].append(name)
        elif maxint == "7":
            city_data_dic["si7"].append(name)

    for i in city_data_dic:
        city_names = city_data_dic[i]
        if city_names:

            if i == "si1":
                tweet_text = "《震度1》"
            elif i == "si2":
                tweet_text = "《震度2》"
            elif i == "si3":
                tweet_text = "《震度3》"
            elif i == "si4":
                tweet_text = "《震度4》"
            elif i == "si5m":
                tweet_text = "《震度5弱》"
            elif i == "si5p":
                tweet_text = "《震度5強》"
            elif i == "si6m":
                tweet_text = "《震度6弱》"
            elif i == "si6p":
                tweet_text = "《震度6強》"
            elif i == "si7":
                tweet_text = "《震度7》"

            for j in city_names:
                tweet_text += j + "、"

            if len(tweet_text) >= 133:
                tweet_text = "{:.133}".format(tweet_text)
                tweet_text = tweet_text.rstrip("、")
                tweet_text = tweet_text + "..."
            else:
                tweet_text = tweet_text.rstrip("、")

            tweet_id = tweet(tweet_text=tweet_text, tweet_id=tweet_id)

    comment = soup.find("forecastcomment").find("text").text.replace("\n", "")
    tweet(tweet_text=comment, tweet_id=tweet_id)


def main(request):
    if request.args and "eew_url" in request.args:
        eew_url = request.args.get("eew_url")
    else:
        return "Hello World!"

    parse_xml(eew_url)
    return "ok"
