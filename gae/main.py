import os
import hmac
import hashlib
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response


app = Flask(__name__)
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
CLOUD_FUNCTIONS_URL = os.environ.get("CLOUD_FUNCTIONS_URL")


def send_eew_url(body):
    soup = BeautifulSoup(body, "lxml")
    entry = soup.find_all("entry")
    for i in entry:
        title = i.find("title").text
        if title == "震源・震度に関する情報":
            eew_url = i.find("link").get("href")
            payload = {"eew_url": eew_url}
            requests.get(CLOUD_FUNCTIONS_URL, params=payload)


@app.route("/sub", methods=["GET"])
def get():
    verify_token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    mode = request.args.get("hub.mode")
    if mode == "subscribe" or mode == "unsubscribe":
        if verify_token == VERIFY_TOKEN:
            result = None if challenge is None else challenge.replace("\n", "") if "\n" in challenge else challenge
            res = Response(response=result, status=200)
            res.headers["Content-Type"] = "text/plain"
            return res
        else:
            return Response("Bad request!", 404)
    else:
        return Response("Bad request!", 404)


@app.route("/sub", methods=["POST"])
def post():
    signature = request.headers["X-Hub-Signature"]
    body = request.get_data(as_text=True)
    hash_ = "sha1=" + hmac.new(bytes(VERIFY_TOKEN, "UTF-8"), bytes(body, "UTF-8"), hashlib.sha1).hexdigest()
    if signature == hash_:

        send_eew_url(body)

        return Response(response="ok", status=200)
    else:
        return Response(response="Bad request!", status=404)


if __name__ == "__main__":
    app.run(threaded=True)
