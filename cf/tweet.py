import os
import re
import tweepy
import mojimoji
import requests
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

    # 取り消しの有無を確認
    infotype = soup.find("infotype").text
    if infotype == "取消":
        return

    # 国内で発生した地震かどうかの確認
    is_domestic = soup.find_all("title")
    if is_domestic[1].text == "遠地地震に関する情報":
        return

    # 発生時刻
    original_time = datetime.strptime(soup.find("origintime").text, "%Y-%m-%dT%H:%M:00+09:00")
    original_time_text = original_time.strftime("%Y年%-m月%-d日 %-H時%-M分ごろ")

    # 震源地 epicenter
    epi_text = soup.find("hypocenter").find("name").text

    # 最大震度 Maximum seismic intensity とり得る値(1, 2, 3, 4, 5-, 5+, 6-, 6+, 7)
    msi = soup.find("intensity").find("maxint").text
    msi_text = msi.replace("-", "弱").replace("+", "強")

    # マグニチュード magnitude
    mag = soup.find("jmx_eb:magnitude").get("description")
    if mag == "不明":
        mag_t = "不明"
    elif mag == "M8を超える巨大地震":
        mag_t = "8以上"
    else:
        mag_t = mojimoji.zen_to_han(mag).replace("M", "")

    # 座標・深さ coordinate
    coor = soup.find("jmx_eb:coordinate")
    if coor.get("description") != "震源要素不明" and coor.get("datum") == "日本測地系":
        coor = re.findall("[+-](\d*[.,]?\d*)", coor.text)
        lat_text = "北緯" + coor[0] + "度"
        lon_text = "東経" + coor[1] + "度"
        depth_text = str(round(int(coor[2]) / 1000)) + "km"
        if depth_text == "0km" or int(depth_text.replace("km", "")) <= 5:
            depth_text = "ごく浅い"
        elif depth_text == "700km":
            depth_text = "700km以上"
    else:
        lat_text = "不明"
        lon_text = "不明"
        depth_text = "不明"

    tweet_text = "【地震情報】\n時刻: {}\n震源地: {}\n最大震度: {}\nマグニチュード: {}\n深さ: {}\n座標: {}/{}".format(original_time_text, epi_text, msi_text, mag_t, depth_text, lat_text, lon_text)
    tweet_img = get_eew_img()
    tweet_id = tweet(tweet_text=tweet_text, tweet_img=tweet_img)

    # 震度毎に市区町村名をツイートする
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
