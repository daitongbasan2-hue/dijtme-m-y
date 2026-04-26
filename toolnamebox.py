import requests
import re
import time
import random
from datetime import datetime

def parse_cookie_string(cookie_string):
    cookie_dict = {}
    cookies = cookie_string.split(";")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.strip().split("=", 1)
            cookie_dict[key] = value
    return cookie_dict

def Headers(setCookies, dataForm=None, Host="www.facebook.com"):
    headers = {
        "Host": Host,
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": f"https://{Host}",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"https://{Host}/",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    if dataForm:
        headers["Content-Length"] = str(len(dataForm))
    return headers

def gen_threading_id():
    return str(
        int(format(int(time.time() * 1000), "b") +
        ("0000000000000000000000" +
        format(int(random.random() * 4294967295), "b"))[-22:], 2)
    )

def dataGetHome(setCookies):
    headers = {
        'Cookie': setCookies,
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
    }

    dictValueSaved = {}

    try:
        c_user = re.search(r"c_user=(\d+)", setCookies)
        dictValueSaved["FacebookID"] = c_user.group(1) if c_user else "0"
    except:
        dictValueSaved["FacebookID"] = "0"

    response = requests.get("https://www.facebook.com", headers=headers)

    fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
    if not fb_dtsg_match:
        fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
    dictValueSaved["fb_dtsg"] = fb_dtsg_match.group(1) if fb_dtsg_match else ""

    jazoest_match = re.search(r'jazoest=(\d+)', response.text)
    if not jazoest_match:
        jazoest_match = re.search(r'name="jazoest" value="(\d+)"', response.text)
    dictValueSaved["jazoest"] = jazoest_match.group(1) if jazoest_match else "22036"

    dictValueSaved["clientRevision"] = "999999999"
    dictValueSaved["cookieFacebook"] = setCookies
    return dictValueSaved

def tenbox(newTitle, threadID, dataFB):
    try:
        message_id = gen_threading_id()
        timestamp = int(time.time() * 1000)
        form_data = {
            "client": "mercury",
            "action_type": "ma-type:log-message",
            "author": f"fbid:{dataFB['FacebookID']}",
            "thread_id": str(threadID),
            "timestamp": timestamp,
            "timestamp_relative": str(int(time.time())),
            "source": "source:chat:web",
            "source_tags[0]": "source:chat",
            "offline_threading_id": message_id,
            "message_id": message_id,
            "threading_id": gen_threading_id(),
            "thread_fbid": str(threadID),
            "thread_name": str(newTitle),
            "log_message_type": "log:thread-name",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }

        response = requests.post(
            "https://www.facebook.com/messaging/set_thread_name/",
            data=form_data,
            headers=Headers(dataFB["cookieFacebook"], form_data),
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )

        if response.status_code == 200:
            return True, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã đổi tên thành: {newTitle}"
        else:
            return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi HTTP {response.status_code} khi đổi tên."
    except Exception as e:
        return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi: {e}"

if __name__ == "__main__":
    print("TOOL ĐỔI TÊN BOX")
    cookie = input("🔐 Nhập cookie Facebook: ").strip()
    thread_id = input("💬 Nhập ID nhóm (thread_fbid): ").strip()
    delay = float(input("⏱️ Nhập delay giữa mỗi lần đổi tên (giây): "))

    try:
        with open("nhay.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Không tìm thấy file nhay.txt!")
        exit(1)

    if not lines:
        print("❌ File nhay.txt không có nội dung!")
        exit(1)

    dataFB = dataGetHome(cookie)
    print(f"🔁 Bắt đầu đổi tên **lặp vô hạn** theo {len(lines)} dòng trong file nhay.txt...\n")

    while True:
        for i, line in enumerate(lines, 1):
            success, log = tenbox(line, thread_id, dataFB)
            print(log)
            time.sleep(delay)