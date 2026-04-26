import os
import re
import gc
import sys
import time
import json
import base64
import random
import string
import asyncio
import threading
import itertools
import smtplib
import ssl
import requests
from io import BytesIO
from enum import Enum
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from textwrap import shorten
from typing import Dict, Any

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button

from anhmess import NanhMessenger
from tooldsbox import get_thread_list
from instagrapi import Client
from toolnamebox import dataGetHome, tenbox
from colorama import Fore
from Crypto.Cipher import AES
from spm import *


# ================== HÀM TIỆN ÍCH ==================

async def send_msg(bot, channelid, msg):
    """Gửi tin nhắn bằng discord.py thay vì requests"""
    channel = bot.get_channel(int(channelid))
    if channel:
        await channel.send(msg)


async def faketyping_discord(bot, channelid, duration: int = 3):
    """Giả typing trong kênh an toàn với discord.py"""
    channel = bot.get_channel(int(channelid))
    if channel:
        async with channel.typing():
            await asyncio.sleep(duration)


async def safe_send(interaction: discord.Interaction, message: str, ephemeral: bool = True):
    """Gửi tin nhắn an toàn (tránh lỗi Unknown Interaction)"""
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(message, ephemeral=ephemeral)
        else:
            await interaction.followup.send(message, ephemeral=ephemeral)
    except discord.NotFound:
        print("[WARN] Interaction expired")


def format_time(seconds: int) -> str:
    """Chuyển số giây thành chuỗi dễ đọc: d, h, m, s"""
    try:
        seconds = int(seconds)
    except Exception:
        return "0s"

    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


# ================== HÀM KIỂM TRA GIỚI HẠN TASK ==================
def check_task_limit(folder: str = "data") -> int:
    if not os.path.exists(folder):
        os.makedirs(folder)
    return len(os.listdir(folder))

# ================= SAFE WRAPPER =================
def safe_thread_wrapper(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(f"[ERROR] Task bị lỗi: {e}")

# ================== FACEBOOK TOOLS (copy từ botv21) ==================
import random, hashlib, json, time, requests

class facebook:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = re.search(r"c_user=(\d+)", cookie).group(1)
        self.fb_dtsg, self.rev, self.jazoest = self._fetch_tokens()

    def _fetch_tokens(self):
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": self.cookie
        }
        r = requests.get("https://www.facebook.com/", headers=headers)
        fb_dtsg = re.search(r'name="fb_dtsg" value="(.*?)"', r.text).group(1)
        rev = re.search(r'"client_revision":(\d+),', r.text).group(1)
        jazoest = re.search(r'name="jazoest" value="(\d+)"', r.text).group(1)
        return fb_dtsg, rev, jazoest


def fbTools(config):
    return {
        "FacebookID": config.get("FacebookID"),
        "fb_dtsg": config.get("fb_dtsg"),
        "clientRevision": config.get("clientRevision"),
        "jazoest": config.get("jazoest"),
        "cookieFacebook": config.get("cookieFacebook")
    }


def generate_offline_threading_id():
    ret = int(random.random() * 2**31)
    time_sec = int(time.time())
    return str((ret << 32) | time_sec)


class MessageSender:
    def __init__(self, fbTools, config, fb):
        self.fbTools = fbTools
        self.config = config
        self.fb = fb
        self.ws_req_number = 1
        self.ws_task_number = 1
        self.mqtt = None  # sẽ connect sau

    def get_last_seq_id(self):
        return 0

    def connect_mqtt(self):
        # trong botv21 dùng lib paho-mqtt để connect
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("[ERROR] Thiếu thư viện paho-mqtt, hãy cài: pip install paho-mqtt")
            return False

        def on_connect(client, userdata, flags, rc):
            print("[MQTT] Connected with result code", rc)

        client = mqtt.Client()
        client.on_connect = on_connect
        try:
            client.connect("edge-mqtt.facebook.com", 443)
            client.loop_start()
            self.mqtt = client
            return True
        except Exception as e:
            print("[MQTT] Không connect được:", e)
            return False

    def stop(self):
        if self.mqtt:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()

# ================= HÀM CHẠY TASK SPAM POLL MESSENGER =================
def start_nhay_poll_func(cookie, idbox, delay, folder_id):
    while True:
        if os.path.exists(f"data/{folder_id}/stop.txt"):
            print(f"[STOP] Task {folder_id} đã dừng.")
            break

        try:
            payload = {
                "av": cookie.split("c_user=")[1].split(";")[0],
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "MessengerGroupPollCreateMutation",
                "variables": json.dumps({
                    "input": {
                        "source": "chat_poll",
                        "question_text": "Bạn thích gì?",
                        "options": [{"text": "Có"}, {"text": "Không"}],
                        "target_id": idbox,
                        "actor_id": cookie.split("c_user=")[1].split(";")[0],
                        "client_mutation_id": str(random.randint(100000, 999999))
                    }
                }),
                "doc_id": "5066134243453369"
            }

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie
            }

            res = requests.post("https://www.facebook.com/api/graphql/", data=payload, headers=headers)
            if res.status_code == 200:
                print(f"[✓] Gửi poll vào box {idbox}")
            else:
                print(f"[×] Lỗi gửi poll ({res.status_code}): {res.text[:100]}")

        except Exception as e:
            print(f"[!] Lỗi khi gửi poll: {e}")

        time.sleep(int(delay))


# ================== DANH SÁCH HÀM OTP (SPM) ==================

functions = [
    send_otp_via_sapo, send_otp_via_viettel, send_otp_via_medicare, send_otp_via_tv360,
    send_otp_via_dienmayxanh, send_otp_via_kingfoodmart, send_otp_via_mocha, send_otp_via_fptdk,
    send_otp_via_fptmk, send_otp_via_VIEON, send_otp_via_ghn, send_otp_via_lottemart,
    send_otp_via_DONGCRE, send_otp_via_shopee, send_otp_via_TGDD, send_otp_via_fptshop,
    send_otp_via_WinMart, send_otp_via_vietloan, send_otp_via_lozi, send_otp_via_F88,
    send_otp_via_spacet, send_otp_via_vinpearl, send_otp_via_traveloka, send_otp_via_dongplus,
    send_otp_via_longchau, send_otp_via_longchau1, send_otp_via_galaxyplay, send_otp_via_emartmall,
    send_otp_via_ahamove, send_otp_via_ViettelMoney, send_otp_via_xanhsmsms, send_otp_via_xanhsmzalo,
    send_otp_via_popeyes, send_otp_via_ACHECKIN, send_otp_via_APPOTA, send_otp_via_Watsons,
    send_otp_via_hoangphuc, send_otp_via_fmcomvn, send_otp_via_Reebokvn, send_otp_via_thefaceshop,
    send_otp_via_BEAUTYBOX, send_otp_via_winmart, send_otp_via_medicare, send_otp_via_futabus,
    send_otp_via_ViettelPost, send_otp_via_myviettel2, send_otp_via_myviettel3, send_otp_via_TOKYOLIFE,
    send_otp_via_30shine, send_otp_via_Cathaylife, send_otp_via_dominos, send_otp_via_vinamilk,
    send_otp_via_vietloan2, send_otp_via_batdongsan, send_otp_via_GUMAC, send_otp_via_mutosi,
    send_otp_via_mutosi1, send_otp_via_vietair, send_otp_via_FAHASA, send_otp_via_hopiness,
    send_otp_via_modcha35, send_otp_via_Bibabo, send_otp_via_MOCA, send_otp_via_pantio,
    send_otp_via_Routine, send_otp_via_vayvnd, send_otp_via_tima, send_otp_via_moneygo,
    send_otp_via_takomo, send_otp_via_paynet, send_otp_via_pico, send_otp_via_PNJ, send_otp_via_TINIWORLD
]

print("B  U  I  - T  U  A  N -  M  A  N  H")            
TOKEN = input("        Token bot: ").strip()
ADMIN_IDS = input("        ID Admin: ").split(",")
ADMIN_IDS = [aid.strip() for aid in ADMIN_IDS]

INTENTS = discord.Intents.default()
INTENTS.members = True

bot = commands.Bot(command_prefix="/", intents=INTENTS)
tree = bot.tree

DATA_FILE = "users.json"
NGONMESS_DIR = "ngonmess_data"
os.makedirs(NGONMESS_DIR, exist_ok=True)
user_tabs = {}
user_nhay_tabs = {}
nhaynameboxzl_tabs = {}
user_zalo_tabs = {}
user_sticker_tabs = {}
TREOSTICKER_LOCK = threading.Lock()
ZALO_LOCK = threading.Lock()
NHAYTAGZALO_LOCK = threading.Lock()
user_nhaytagzalo_tabs = {}
TAB_LOCK = threading.Lock()
user_poll_tabs = {}
POLL_LOCK = threading.Lock()
user_image_tabs = {}
IMAGE_TAB_LOCK = threading.Lock()
user_nhaymess_tabs = {}
NHAY_LOCK = threading.Lock()
user_discord_tabs = {}
DIS_LOCK = asyncio.Lock()
user_nhaydis_tabs = {}  
NHAYDIS_LOCK = asyncio.Lock()
user_treotele_tabs = {}   
TREOTELE_LOCK = threading.Lock()
SPAM_TASKS = {}  
TREOSMS_TASKS = {}
TREOSMS_LOCK = threading.Lock()
IG_LOCK = threading.Lock()
user_treogmail_tabs = {}
user_nhaynamebox_tabs = {}
NHAYNAMEBOX_LOCK = threading.Lock()
TREOSMS_TASKS = {}
user_reostr_tabs = {}
TREOSMS_LOCK = threading.Lock()
TREOGMAIL_LOCK = threading.Lock()
user_nhaytag_tabs = {}
NHAYTAG_LOCK = threading.Lock()


if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(interaction: discord.Interaction):
    return str(interaction.user.id) in ADMIN_IDS

def is_authorized(interaction: discord.Interaction):
    users = load_users()
    uid = str(interaction.user.id)
    if uid in users:
        exp = users[uid]
        if exp is None:
            return True
        elif datetime.fromisoformat(exp) > datetime.now():
            return True
        else:            
            _remove_user_and_kill_tabs(uid)
    return False

def is_owner(interaction: discord.Interaction) -> bool:
    """Admin chính (ID bạn nhập khi start bot)."""
    uid = str(interaction.user.id).strip()
    return uid in [aid.strip() for aid in ADMIN_IDS if aid.strip()]

def is_subadmin(interaction: discord.Interaction) -> bool:
    """Admin phụ (thêm bằng /addadmin, lưu trong users.json)."""
    return is_authorized(interaction)

def has_permission(interaction: discord.Interaction) -> bool:
    """Quyền chung: Admin chính hoặc Admin phụ."""
    return is_owner(interaction) or is_subadmin(interaction)





def _add_user(uid: str, days: int = None):
    users = load_users()
    if days:
        expire_time = (datetime.now() + timedelta(days=days)).isoformat()
        users[uid] = expire_time
    else:
        users[uid] = None
    save_users(users)

def _remove_user_and_kill_tabs(uid: str):
    users = load_users()
    if uid in users:
        del users[uid]
        save_users(users)
    with TAB_LOCK:
        if uid in user_tabs:
            for tab in user_tabs[uid]:
                tab["stop_event"].set()
            del user_tabs[uid]

def _get_user_list():
    users = load_users()
    result = []
    for uid, exp in users.items():
        if exp:
            remaining = datetime.fromisoformat(exp) - datetime.now()
            if remaining.total_seconds() <= 0:
                continue  
            days = remaining.days
            hours, rem = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            time_str = f"{days} ngày, {hours} giờ, {minutes} phút"
            result.append((uid, time_str))
        else:
            result.append((uid, "vĩnh viễn"))
    return result
    
def extract_facebook_post_id(link):
    match = re.search(r"fbid=(\d+)", link)
    if not match:
        match = re.search(r"/posts/(\d+)", link)
    if not match:
        match = re.search(r"/videos/(\d+)", link)
    if not match:
        match = re.search(r"/permalink/(\d+)", link)
    return match.group(1) if match else None

def get_token(cookie):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'cache-control': 'max-age=0',
        'cookie': cookie,
        'dpr': '1',
        'priority': 'u=0, i',
        'sec-ch-prefers-color-scheme': 'light',
        'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="125.0.6422.78", "Chromium";v="125.0.6422.78", "Not.A/Brand";v="24.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'viewport-width': '868',
    }

    try:
        response = requests.get('https://business.facebook.com/content_management', headers=headers).text
        token = response.split('[{"accessToken":"')[1].split('","')[0]
        return token
    except Exception as e:
        print(f'\033[1;31mLấy Token Thất Bại')
        return None

def check_login_facebook(cookie):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": cookie
        }
        res = requests.get("https://mbasic.facebook.com/profile.php", headers=headers)
        name_match = re.search(r'<title>(.*?)</title>', res.text)
        uid_match = re.search(r'c_user=(\d+)', cookie)
        fb_dtsg = re.search(r'name="fb_dtsg" value="(.*?)"', res.text)
        jazoest = re.search(r'name="jazoest" value="(.*?)"', res.text)

        if "login" in res.url or not uid_match:
            return None
        return (
            name_match.group(1) if name_match else "No Name",
            fb_dtsg.group(1) if fb_dtsg else "",
            jazoest.group(1) if jazoest else "",
            uid_match.group(1)
        )
    except:
        return None

def auto_cmt_moi_ne(token, idpost, noidung, image_url, cookie):
    try:
        url = f"https://graph.facebook.com/v19.0/{idpost}/comments"
        payload = {
            "message": noidung,
            "attachment_url": image_url,
            "access_token": token
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": cookie
        }
        res = requests.post(url, headers=headers, data=payload)
        if res.status_code != 200:
            return {"error": True, "msg": res.text}
        return res.json()
    except Exception as e:
        return {"error": True, "msg": str(e)}

def visual_delay(seconds):
    for remaining in range(int(seconds), 0, -1):
        print(f"\r{COLORS['vang']}   → Delay: {remaining}s ", end="", flush=True)
        time.sleep(1)
    print()
        
def image_tab_worker(
    post_id: str,
    cookies_raw: str,
    message: str,
    images: list[str],
    tag_id: str,
    delay_min: float,
    delay_max: float,
    stop_event: threading.Event,
    start_time: datetime,
    discord_user_id: str
):
    cookies = [ck.strip() for ck in cookies_raw.split(",") if ck.strip()]
    if not cookies:
        print(f"Không có cookie hợp lệ.")
        return

    cookie = cookies[0]  # chỉ lấy cookie đầu tiên, không chuyển cookie khác
    success_count = 0

    while not stop_event.is_set():
        try:
            login_info = check_login_facebook(cookie)
            if not login_info:
                print("Login thất bại, vẫn tiếp tục...")
            else:
                name, _, _, uid = login_info
                print(f"Dùng cookie: {name} | UID: {uid}")

                token = get_token(cookie)
                if not token:
                    print("Không lấy được token, vẫn tiếp tục...")
                else:
                    image_url = random.choice(images)
                    noidung = message
                    if tag_id:
                        noidung += f' @[{tag_id}:0]'

                    response = auto_cmt_moi_ne(token, post_id, noidung, image_url, cookie)

                    if isinstance(response, dict) and "error" in response:
                        print(f"Lỗi gửi comment: {response['msg']}")
                    else:
                        success_count += 1
                        print(f"Gửi thành công {success_count} lần | ID comment: {response.get('id')}")

        except Exception as e:
            print(f"Lỗi ngoại lệ: {e}")

        # Delay luôn được thực hiện dù có lỗi
        delay = random.uniform(delay_min, delay_max)
        for remaining in range(int(delay), 0, -1):
            if stop_event.is_set():
                break
            print(f"Delay: {remaining}s ", end="\r")
            time.sleep(1)
        if not stop_event.is_set():
            time.sleep(delay - int(delay))

    print(f"Tab ANHTOP user {discord_user_id} đã dừng.")
    
def _remove_user_and_kill_tabs(uid: str):
    users = load_users()
    if uid in users:
        del users[uid]
        save_users(users)
    with TAB_LOCK:
        if uid in user_tabs:
            for tab in user_tabs[uid]:
                tab["stop_event"].set()
            del user_tabs[uid]

    with IMAGE_TAB_LOCK:
        if uid in user_image_tabs:
            for tab in user_image_tabs[uid]:
                tab["stop_event"].set()
            del user_image_tabs[uid]
            


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://chat.zalo.me",
    "Referer": "https://chat.zalo.me/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
}

def now():
    return int(time.time() * 1000)

def zalo_encode(params, key):
    key = base64.b64decode(key)
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = json.dumps(params).encode()
    pad_len = AES.block_size - len(plaintext) % AES.block_size
    padded = plaintext + bytes([pad_len] * pad_len)
    return base64.b64encode(cipher.encrypt(padded)).decode()

def zalo_decode(encrypted_data, key):
    key = base64.b64decode(key)
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(base64.b64decode(encrypted_data))
    pad_len = decrypted[-1]
    return decrypted[:-pad_len].decode('utf-8', errors='ignore')

class ThreadType(Enum):
    USER = 1
    GROUP = 2

class ZaloAPI:
    def __init__(self, imei, cookies):
        self.session = requests.Session()
        self.imei = imei
        self.secret_key = None
        self.uid = None
        self.session.headers.update(HEADERS)
        self.session.cookies.update(cookies)
        self.login()

    def login(self):
        url = "https://wpa.chat.zalo.me/api/login/getLoginInfo"
        params = {"imei": self.imei, "type": 30, "client_version": 645, "ts": now()}
        response = self.session.get(url, params=params)
        try:
            data = response.json()
        except Exception:
            raise Exception("❌ Không thể phân tích JSON từ phản hồi!")

        user_data = data.get("data")
        if not isinstance(user_data, dict):
            print("⚠️ Phản hồi không hợp lệ hoặc sai IMEI/Cookie:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            raise Exception("❌ Không nhận được thông tin người dùng (user_data)")

        self.uid = user_data.get("send2me_id")
        self.secret_key = user_data.get("zpw_enk")
        if not self.secret_key:
            raise Exception("❌ Không lấy được secret_key")

    def fetch_groups(self):
        url = "https://tt-group-wpa.chat.zalo.me/api/group/getlg/v4"
        params = {"zpw_ver": 645, "zpw_type": 30}
        response = self.session.get(url, params=params)
        data = response.json()
        decoded = zalo_decode(data["data"], self.secret_key)
        parsed = json.loads(decoded)
        grid_map = parsed.get("data", {}).get("gridVerMap", {})
        groups = []
        for group_id in sorted(grid_map.keys(), key=lambda x: int(x)):
            info = self.fetch_group_info(group_id)
            groups.append({
                "id": group_id,
                "name": info["name"],
                "members": info["totalMember"]
            })
        return groups

    def fetch_group_info(self, group_id):
        url = "https://tt-group-wpa.chat.zalo.me/api/group/getmg-v2"
        params = {"zpw_ver": 645, "zpw_type": 30}
        encoded = zalo_encode({"gridVerMap": json.dumps({str(group_id): 0})}, self.secret_key)
        response = self.session.post(url, params=params, data={"params": encoded})
        result = response.json()
        decoded = zalo_decode(result["data"], self.secret_key)
        parsed = json.loads(decoded)
        info = parsed.get("data", {}).get("gridInfoMap", {}).get(str(group_id), {})
        return {
            "name": info.get("name", "(Không rõ tên)"),
            "totalMember": info.get("totalMember", "?")
        }

    def fetch_friends(self):
        url = "https://profile-wpa.chat.zalo.me/api/social/friend/getfriends"
        params = {"zpw_ver": 645, "zpw_type": 30}
        encoded = zalo_encode({"offset": 0, "count": 1000}, self.secret_key)
        response = self.session.post(url, params=params, data={"params": encoded})
        result = response.json()
        decrypted = zalo_decode(result["data"], self.secret_key)
        parsed = json.loads(decrypted)
        data_section = parsed.get("data", [])
        if isinstance(data_section, list):
            users = data_section
        else:
            users = data_section.get("users", [])
        return [{"id": u.get("userId"), "name": u.get("zaloName", "(Không rõ tên)")} for u in users]

    def send_message(self, message, thread_id, thread_type):
        url = "https://tt-group-wpa.chat.zalo.me/api/group/sendmsg" if thread_type == ThreadType.GROUP else "https://tt-chat2-wpa.chat.zalo.me/api/message/sms"
        payload = {
            "message": message,
            "clientId": str(now()),
            "imei": self.imei
        }
        if thread_type == ThreadType.GROUP:
            payload["visibility"] = 0
            payload["grid"] = str(thread_id)
        else:
            payload["toid"] = str(thread_id)
        encoded = zalo_encode(payload, self.secret_key)
        response = self.session.post(url, params={"zpw_ver": 645, "zpw_type": 30}, data={"params": encoded})
        return response.json()

    def set_typing_real(self, thread_id, thread_type):
        params = {"zpw_ver": 645, "zpw_type": 30}
        payload = {
            "params": {
                "imei": self.imei
            }
        }
        if thread_type == ThreadType.USER:
            url = "https://tt-chat1-wpa.chat.zalo.me/api/message/typing"
            payload["params"]["toid"] = str(thread_id)
            payload["params"]["destType"] = 3
        elif thread_type == ThreadType.GROUP:
            url = "https://tt-group-wpa.chat.zalo.me/api/group/typing"
            payload["params"]["grid"] = str(thread_id)
        else:
            raise Exception("Invalid thread type")
        encoded = zalo_encode(payload["params"], self.secret_key)
        self.session.post(url, params=params, data={"params": encoded})


class SpamTool(ZaloAPI):
    def __init__(self, name, imei, cookies, thread_ids, thread_type, use_typing=False):
        super().__init__(imei, cookies)
        self.name = name
        self.thread_ids = thread_ids
        self.thread_type = thread_type
        self.use_typing = use_typing
        self.running = False  # Mặc định là chưa chạy

    def send_spam(self, messages, delay):
        self.running = True  # Bắt đầu chạy

        while self.running:
            for thread_id in self.thread_ids:
                for message in messages:
                    if not self.running:
                        break  # Dừng ngay nếu có yêu cầu

                    try:
                        if self.use_typing:
                            print(f"[ZALO#{thread_id}] ✍️ Đang soạn tin...")
                            self.set_typing_real(thread_id, self.thread_type)
                            time.sleep(1.5)  # delay ngắn để giả lập soạn

                        result = self.send_message(message, thread_id, self.thread_type)

                        short_msg = (message[:50] + "...") if len(message) > 50 else message
                        print(f"[ZALO#{thread_id}] ✅ Thành công → {thread_id} | Nội dung: {short_msg}")
                    except Exception as e:
                        print(f"[ZALO#{thread_id}] ❌ Lỗi: {e}")

                    time.sleep(delay)

        print(f"[{self.name}] ⛔ Đã dừng spam.")
        
@tree.command(
    name="nhaytop",
    description="Treo nhây top"
)
@app_commands.describe(
    cookies="Cookie",
    post_link="Link bài viết",
    delay="Delay",
    tag_id="ID cần tag"
)
async def nhaytop(
    interaction: discord.Interaction,
    cookies: str,
    post_link: str,
    delay: float,
    tag_id: str = None
):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")

    cookie_list = [normalize_cookie(c.strip()) for c in cookies.split(",") if c.strip()]
    if not cookie_list:
        return await interaction.response.send_message("Cookie không hợp lệ")

    if delay < 0.5:
        return await interaction.response.send_message("Delay phải trên 0.5s")

    post_id, group_id = extract_post_group_id(post_link)
    if not post_id or not group_id:
        return await interaction.response.send_message("Link không đúng định dạng group/post")

    stop_event = threading.Event()
    start_time = datetime.now()
    discord_user_id = str(interaction.user.id)

    th = threading.Thread(
        target=nhaytop_worker,
        args=(cookie_list, delay, post_id, group_id, tag_id, stop_event, start_time, discord_user_id),
        daemon=True
    )
    th.start()

    with NHAY_LOCK:
        if discord_user_id not in user_nhay_tabs:
            user_nhay_tabs[discord_user_id] = []
        user_nhay_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "post_id": post_id,
            "group_id": group_id,
            "delay": delay,
            "tag_id": tag_id
        })

    await interaction.response.send_message(
        f"Đã tạo tab nhây top cho <@{discord_user_id}>:\n"
        f"• GroupID: `{group_id}` | PostID: `{post_id}`\n"
        f"• Delay: `{delay}` giây\n"
        f"{'• Tag UID: '+tag_id if tag_id else ''}\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
         

raw_spam_list = [
    "ccho sua lofi de {chon_name}",
    "sua di {chon_name} em😏🤞",
    "lofi di {chon_name} cu😝",
    "tk ngu lon {chon_name} eyy🤣🤣",
    "nhanh ti em {chon_name}🤪👌",
    "cam a {chon_name} mo coi😏🤞",
    "hang hai len ti {chon_name} de👉🤣",
    "cn tat nguyen {chon_name}😏??",
    "cn 2 lai mat mam {chon_name}🤪👎",
    "anh cho may sua a {chon_name}😏🤞",
    "ah ba meta 2025 ma {chon_name}😋👎",
    "bi anh da na tho cmnr dk {chon_name}🤣",
    "thieu oxi a {chon_name}🤣🤣",
    "anh cko may oxi hoa ne {chon_name}😏👉🤣",
    "may cay cha qua a cn ngu {chon_name}🤪",
    "may phe nhu con me may bi tao hiep ma {chon_name}🤣",
    "dung ngam dang nuot cay tao nha coan {chon_name}👉🤣",
    "con cho {chon_name} cay tao ro👉🌶",
    "oc cho ngoi do nhay voi tao a {chon_name}🤣",
    "me may bi tao cho len dinh r {chon_name}=))",
    "ui cn ngu {chon_name} oc cac=))",
    "cn gai me may khog bt day nay a {chon_name} cn oc cac😝",
    "cn cho {chon_name} may cam a:))?",
    "cam lang that r a cn ngu {chon_name}🤣",
    "ui tk cac dam cha chem chu ak {chon_name}😝🤞",
    "cn cho dot so tao run cam cap me roi ha em {chon_name} =))",
    "ui cai con hoi {chon_name}👉🤣",
    "cn me may chet duoi ao roi kia {chon_name}😆",
    "djt con {chon_name} cu cn lon tham:))",
    "ui con bem {chon_name} nha la nhin phen v:))",
    "con cho cay gan nha sua di {chon_name}😏",
    "con bem {chon_name} co me khog😏🤞",
    "a quen may mo coi tu nho ma {chon_name}🤣",
    "sua chill de {chon_name} oc🤣",
    "hay cam nhan noi dau di em {chon_name}:))))",
    "hinh anh con bem {chon_name} gie rach bi anh cha dap:))))))",
    "ti anh chup dang tbg la may hot nha {chon_name}🤣",
    "a may muon hot cx dau co de cn ngu {chon_name}👉🤣🤣",
    "oi may bi cha suc pham kia {chon_name}-))",
    "tao co noti con boai {chon_name} so tao:)) ti tao cap dang profile 1m theo doi:))",
    "{chon_name} con o moi khong bame bi tao khinh thuong=)))",
    "may con gi khac hon khong con bem du ngu {chon_name}🤣",
    "cam canh cdy ngu bi cha chui khong giam phan khang a {chon_name}:))",
    "bi tao chui ma toi so a {chon_name}🤞",
    "nhin ga {chon_name} muon ia chay🤣",
    "con culi lua thay phan ban bi phan boi a {chon_name}:))",
    "may bi tao chui cho om han dk {chon_name}👉🤣🤣🤞",
    "bi tao chui cho so queo cac dung khong {chon_name}:))))",
    "dung cam han tao nua {chon_name}:))",
    "con dog {chon_name} bi tao chui ghi thu a:))",
    "su dung ngon sat thuong xiu de bem anh di mo {chon_name}=)))",
    "co sat thuong chi mang ko ay {chon_name}😝",
    "con ngheo nha la {chon_name} bi bo si va👉🤣🤣",
    "nao may co biet thu nhu anh vay {chon_name}🤪👌",
    "thang nghich tu {chon_name} sao may giet cha may the:))",
    "khong ngo thang phan nghich {chon_name} lua cha doi me=))",
    "tk ngu {chon_name} bi anh co lap ma-))",
    "phan khang di con cali {chon_name} mat map:))",
    "may con gi khac ngoai sua khong ay {chon_name}👉😏🤞",
    "{chon_name} mo coi=))",
    "bi cha chui phat nao ghi han phat do {chon_name} dk em:))",
    "may toi day de chi bi tao chui thoi ha {chon_name}:))",
    "bo la ac quy fefe ne {chon_name}🤣🤣",
    "nen bo lay cay ak ban nat so may luon😏🤞",
    "keo lu ban an hai may ra lmj dc anh khong vay {chon_name}🤣🤞",
    "ui ui dung thang an hai mang ten {chon_name}:))",
    "dung la con can ba mxh chi biet nhin anh chui cha mang me no ma {chon_name}=))",
    "may co phan khang duoc khong vay:)) {chon_name}",
    "may khong phan khang duoc a {chon_name}=))",
    "may yeu kem den vay a con cali {chon_name}😋👎",
    "con cali {chon_name} mat mam cay ah roi🌶",
    "cu anh lam dk em {chon_name}:))",
    "may co biet gi ngoai sua kiki dau ma {chon_name}👉🤣🤣",
    "may la chi qua qua ban may la chi gau gau ha {chon_name}=))",
    "mua skill di em {chon_name}🤪🤞",
    "anh mua skill duoc ma em {chon_name}😏🤞",
    "anh mua skill vo cai lon me may ay em {chon_name}:))",
    "con culi {chon_name} said : sap win duoc anh roi mung vai a🤣",
    "con cali {chon_name} nghi vay nen mung lam dk:)) {chon_name}",
    "win duoc anh dau de dau em {chon_name}🤪🤞",
    "con cho dien {chon_name} sua dien cuong nao🤣",
    "ui ui con kiki {chon_name} cay anh da man a🌶",
    "tk mo coi {chon_name} sua belike a🤣",
    "chill ti di em {chon_name}🤣🤣",
    "m còn trò gì thể hiện nhanh lên ơ kìa {chon_name}",
    "ơ hay óc chó ơi m sủa mạnh mẽ lên sao lại bị dập rồi {chon_name}",
    "lêu lêu thằng ngu không làm gì được cay anh kìa {chon_name}",
    "haha óc chó gà bị chửi cay cú ớt mẹ rồi =))) {chon_name}",
    "óc chó ngu nghèo cay cha bán mạng đi chửi cha má kìa =)))) {chon_name}",
    "m chạy đâu vậy con chó ngu ơi không được chạy mà :((( {chon_name}",
    "ai đụng gì óc chó để nó sợ rồi chạy thục mạng kìa {chon_name}",
    "culi ngu bị anh chửi té tát nước vô mặt m kìa =))) {chon_name}",
    "em bé khóc kìa ai cứu nó đi 😹😹 {chon_name}",
    "culi bị chửi mất xác kìa 😹😹😹 {chon_name}",
    "cha bá sàn mà {chon_name}",
    "cha bá all sàn mà bọn óc 🤪 {chon_name}",
    "thằng ngu giết cha bóp cổ má để cầu win anh à 😏👉 {chon_name}",
    "hi vọng làm dân war của con ngu bị tao dập tắt từ khi nó sủa điên trước mặt tao ae =))) {chon_name}",
    "bà nội m loạn luân với bố m còn ông ngoại loạn luân với mẹ m mà thằng não cún =)) 🤪 {chon_name}",
    "con thú mại dâm bán dâm mà như bán trinh hoa hậu vậy 🤣 {chon_name}",
    "con ngu nứng quá đến cả con mẹ nó gần u60 rồi nó vẫn không tha =)) {chon_name}",
    "mẹ mày làm con chó canh cửa cho nhà tao mà 🤣 {chon_name}",
    "đáp ngôn nhanh hơn tý được không thằng ngu xuẩn {chon_name}",
    "bắt quả tang con chó chạy bố nè {chon_name}",
    "não cún chỉ biết âm thầm seen và ôm gối khóc mà huhuh 👈😜 {chon_name}",
    "con cave này adr 16gb đang kiếm tiền mua iPhone được 🤣🤣 {chon_name}",
    "vào một hôm bỗng con đĩ mẹ mày die thì lúc đó cha làm bá chủ sàn mẹ rồi :)) {chon_name}",
    "con đĩ mẹ mày bất lực vì bị tao chửi mà chỉ biết câm lặng :)) {chon_name}",
    "mẹ mày bị tao đụ đột quỵ ngoài nhà nghỉ kìa đem hòm ra nha {chon_name}",
    "đem hai cái mày với con mẹ m luôn nha {chon_name}",
    "thời gian trôi qua để cảm nhận nỗi đau đi ửa à {chon_name}",
    "nhai tao chặt đầu con đĩ má mày ra đó {chon_name}",
    "thằng ngu LGBT da đen sủa lẹ ai cho mày câm {chon_name}",
    "thằng sex thú đang cố làm cha cay hả thằng bại não {chon_name}",
    "tao miễn nhiễm mà thằng ngu {chon_name}",
    "mẹ mày bị cha đụ từ Nam vào đến Bắc mà 🤪👊 {chon_name}",
    "mẹ mày banh háng cho khách đụ kìa thằng óc {chon_name}",
    "tao lỡ cho mẹ mày bú cu tao rồi sướng vãi cặc 🧐🤙 {chon_name}",
    "lêu lêu nhìn cha đụ mẹ mày không làm được gì à đừng có cay cha nha 😝👎 {chon_name}",
    "bị tao khủng bố quá nát mẹ cái hộp sọ với não luôn rồi à =)) {chon_name}",
    "mày là con đĩ đầu đinh giết má để loạn luân với bố mà con khốn {chon_name}",
    "văn thơ anh lai láng để con mẹ m dạng háng mỗi đêm =))) {chon_name}",
    "qua sông thì phải bắc cầu kiều con mẹ mày muốn làm đĩ thì phải yêu chiều các anh mà 🤣👈 {chon_name}",
    "con lồn ngu này hay đạp xe đạp ngang nhà tao bị tao chọi đá về méc mẹ mà 🤣 {chon_name}",
    "thằng ngu này đang đi bộ bị t đánh úp nó về mách mẹ mà ae 🤣🤣 {chon_name}",
    "thằng đầu đinh ở nhà lá mà ae nó mơ ước được ở biệt thự như tui =)) {chon_name}",
    "cả họ nhà mày phải xếp hàng lần lượt bú dái t mà 🤣🤣 {chon_name}",
    "thằng ảo war bị tao chửi cố gắng phản kháng nhưng nút home không cho phép mày cay quá đập cmn máy 🤣👈 {chon_name}"
    "sống như 1 con chó ngu dốt như lũ phèn ói chợ búa cầm dao múa kiếm {chon_name}",
    "cha mày hóa thân thành hắc bạch vô thường cha mày bắt hồn đĩ mẹ mày xuống chầu diêm vương {chon_name}",
    "nghèo bần hèn bị cha mày đứng trên đạp đầu lũ đú chúng mày cha đi lên {chon_name}",
    "đú má mày tới tháng xịt nước máu kinh cho thk cha mày uống {chon_name}",
    "mày đi học bị bạn bè chê xài nút home mày cay quá về đánh đập bà già kêu bả làm đĩ để có tiền mua điện thoại mới đi sĩ với bạn bè =)) {chon_name}",
    "con điếm phò mã bị cha mày cầm cái cây chà bồn cầu cha chà nát lồn mày nè {chon_name}",
    "đừng có lên mạng xã hội tạo nét mà bị anh hành là mếu máo đi cầu cứu ngay {chon_name}",
    "mày thấy anh chửi thấm quá và nghĩ trong đầu là anh này bá vcl đéo chửi lại nó đâu :))) {chon_name}",
    "thằng này đang ăn bị t đứng trên nóc nhà nó t ỉa trúng bát cơm nó luôn mà ae {chon_name}",
    "mày bí ngôn tới nỗi phải lên google ghi : những câu chửi nhau hay nhất để phản kháng tao mà 🤣👈 {chon_name}",
    "mày thấy a chửi hay quá nên xin làm đệ của a để được kéo làm hw à :))) {chon_name}",
    "mày bị chửi tới nỗi tăng huyết áp phải cầu xin anh tha thứ :))) {chon_name}",
    "người yêu nó bị t đụ rên ư ử khen ku a trung to và dài thế :)))) {chon_name}",
    "mẹ nó khen cặc t to chấp nhận bỏ ba nó vì ông ấy yếu sinh lý :))) {chon_name}",
    "cha nó ôm hận t lắm chỉ biết đứng ôm cặc khóc trong vô vọng :))) {chon_name}",
    "mẹ nó bị t đụ chán chê xong bị t trap t yêu người mẫu mà 🤣👈 {chon_name}",
    "con bướm trâu bị gái có cu yêu qua mạng trap =))) {chon_name}",
    "trăng kia ai vẽ mà tròn loz con mẹ m bị ai địt mà mòn 1 bên 🤣 {chon_name}",
    "mẹ m có phải còn búp bê tình dục để a lục đục mỗi đêm không 😏? {chon_name}",
    "mẹ m thì xóc lọ cho t còn người ta thì kính lão đắc thọ {chon_name}",
    "m tin bố lấy yamaha bố đề số 3 bố tông vào loz con đĩ mẹ m không {chon_name}",
    "m gặp các anh đây toàn đấng tối cao a cầm con dao a đâm a thọc a chọc vào cái lỗ loz con mẹ m mà 🤣👈 {chon_name}",
    "cha m lấy gạch ống chọi nát cái đầu mu lồn mẹ mày giờ con bẻm đú {chon_name}",
    "con mồ côi mày mà rớt là tao lấy chiếc xe rùa t cán lòi mu lồn mẹ m đó gán trụ nha {chon_name}",
    "cú đấm sấm sét của anh đấm nát cái lồn mẹ thằng chó đú nhây như mày🤣👈 {chon_name}",
    "cú đá cuồng phong đá bung cái lồn mẹ mày nè thằng não cặc🤣👈 {chon_name}",
    "anh lấy cái ô tô anh đâm thẳng dô cái lồn con gái mẹ thằng súc vật như m {chon_name}",
    "hôm nay anh sẽ thay trời hành đạo anh cạo nát cái lông lồn con gái mẹ mày đó nghe chưa {chon_name}",
    "con đĩ eo di bi ti bị mẹ mày hành cho tới đột quỵ k có tiền lo t//ang lễ phải quỳ qua háng tao van xin tao cho tiền đúng kh {chon_name}",
    "thằng cặc chứng kiến cái cảnh mẹ nó bị t cầm bật lửa đốt từng cộng lông bướm:))) {chon_name}",
    "anh gõ chết con đĩ mẹ mày giờ mày sủa ngôn có sthuong tý coi em nhìn em phèn dạ anh mày chửi luôn ông bà mày đái lên mặt mày nè con sút vật yếu kém {chon_name}",
    "thằng óc cặc bị tao ném xuống ao nhưng béo quá bị chết chìm🐕 {chon_name}",
    "mày bị tao hành hung cho sắp đột tử rồi kìa kêu con đĩ mẹ mày qua cứu vãn mày lẹ đi không là tao cho mày nằm quan tài gào khóc thảm thiết trong đó liền ngay 3s nè con đĩ phế {chon_name}",
    "nhanh lên con chó lồn khai khắm=)) {chon_name}",
    "con gái mẹ mày die dưới tay bọn anh kìa {chon_name}",
    "thằng bẻm bị t thọc cặc lên ổ cứng phát não rớt ra ngoài=))) {chon_name}",
    "cạn bã của xã hội mà tưởng mình hay hã con thú🤣💨 {chon_name}",
    "thằng óc dái khi nghe tin cha nó chết kiểu: úi úi thằng già này cuối cùng cũng chết r vui vl=)) {chon_name}",
    "thằng lồn ảo anime bật gear 5 lên địt con già nó trước bàn thờ tổ tiên=)) {chon_name}",
    "anh là cha dượng của bọn mày mà tụi bú cứt 🤣 {chon_name}",
    "đây là suy nghĩ của con ngu sau khi nó bị tao sỉ nhục trong đầu nó bây giờ kiểu: quân tử trả thù 10 năm chưa muộn :))))) {chon_name}",
    "thằng ngu bị tao áp đảo từ phút 1 tới giờ nó k có cơ hội để sủa luôn ae=))) {chon_name}",
    "thằng đú bot mời ae nó sang nhà đụ bà già nó free vì hôm nay là ngày vui vì cha nó mới qua đời=)) {chon_name}",
    "thằng cặc bị tao hạ đo ván sau 1 cú sút ngoạn mục đến từ vị trí anh mà=))) {chon_name}",
    "thằng óc cặc đòi va anh và cái kết bị anh chửi chạy khắp nơi=)) {chon_name}",
    "mẹ mày bị tao địt rách màn trinh mà🤪 {chon_name}",
    "🤭🤭Mày bê đê ngũ sắc dell công khai bị tao chọc quá máu cặc mày dồn lên não choa mày chết hả {chon_name}",
    "nhà thằng đú này nghèo không có tiền chơi gái nên phải loạn luân luôn với mẹ nó để giải khát cơn thèm thuồng {chon_name}",
    "thằng cầm thú loạn luân some với mẹ ruột và ba ruột còn quay clip {chon_name}",
    "m bị óc cứt hay sao z hả mà t nói m dell hiểu hay bố phải nhét cứt vào đầu m thì m mới thông hả con óc lồn ơi {chon_name}",
    "Một lũ xam cu lên đây đú ửa ngôn thì nhạt như cái nước lồn của con đỉ mẹ cm v hăng lên đi con mẹ mày bị t xé rách mu sao chối ???? {chon_name}",
    "bà già mày bị tao treo cổ lên trên trần nhà mà? {chon_name}",
    "thằng bất tài vô dụng sủa mạnh lên đi {chon_name}",
    "cố gắng để win tao nhá {chon_name}",
    "tao bất bại mà thằng ngu? {chon_name}",
    "mẹ mày bị t đầu độc đến chết mà {chon_name}",
    "mày đàn ông hay đàn bà yếu đuối vậy {chon_name}",
    "con chó đầu đinh bị anh cầm cái đinh ba a thọc vào lỗ nhị nó mà ae =)) {chon_name}",
    "thằng như mày xứng đáng ăn cứt tao á {chon_name}",
    "Nghe Cha Chửi Chết Con Gái Mẹ Mày Nè Con Ngu {chon_name}",
    "Mẹ Mày Bị Tao Lấy Phóng Lợn Chọt Dô Mu Lồn Khi Đang Đi Làm Gái Ở Ngã 3 Trần Duy Hưng🤣👈 {chon_name}",
    "con mẹ m nghe tin m loạn luân vs bố m nên lấy dao cắt cổ tự tử r kìa con ngu :)) {chon_name}",
    "m tìm câu nào sát thương tí được k thằng nghịch tử đâm bố đụ mẹ :)) 🤣 {chon_name}",
    "óc chó bị anh chửi nhớ cha nhớ mẹ nhớ kiếp trước kìa😹😹😹 {chon_name}",
    "Khẩu phần ăn của mẹ m là cứt mà😜 {chon_name}",
    "Mẹ m bị anh treo cổ mà😜 {chon_name}"    
 ]

def nhaytop_worker(
    cookie_list: list[str],
    delay: float,
    post_id: str,
    group_id: str,
    tag_id: str,
    stop_event: threading.Event,
    start_time: datetime,
    discord_user_id: str
):
    index_ck = 0
    line_index = 0

    while not stop_event.is_set():
        cookie = cookie_list[index_ck % len(cookie_list)]
        user_id, fb_dtsg, rev, req, a, jazoest = get_uid_fbdtsg(cookie)
        if not (user_id and fb_dtsg and jazoest):
            index_ck += 1
            continue

        chon_name = ""
        if tag_id:
            info = get_info(tag_id, cookie, fb_dtsg, a, req, rev)
            if "name" in info:
                chon_name = info["name"]
        
        raw = raw_spam_list[line_index % len(raw_spam_list)]
        line_index += 1
        content = raw.replace("{chon_name}", chon_name).strip()

        ok = cmt_gr_pst(
            cookie, group_id, post_id, content,
            user_id, fb_dtsg, rev, req, a, jazoest,
            uidtag=tag_id, nametag=chon_name if tag_id else None
        )
        status = "OK" if ok else "FAIL"
        uptime = get_uptime(start_time)
        print(f"[NHAY][{discord_user_id}] → {group_id}/{post_id} | {status} | Uptime:{uptime}".ljust(120), end="\r")

        for _ in range(int(delay)):
            if stop_event.is_set(): break
            time.sleep(1)
        if stop_event.is_set(): break
        time.sleep(delay - int(delay))

        if not ok:
            index_ck += 1

    print(f"\\nTab NHAYTOP của user {discord_user_id} đã dừng.")
    
def get_guid():
    section_length = int(time.time() * 1000)
    
    def replace_func(c):
        nonlocal section_length
        r = (section_length + random.randint(0, 15)) % 16
        section_length //= 16
        return hex(r if c == "x" else (r & 7) | 8)[2:]

    return "".join(replace_func(c) if c in "xy" else c for c in "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx")

def normalize_cookie(cookie, domain='www.facebook.com'):
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(f'https://{domain}/', headers=headers, timeout=10)
        if response.status_code == 200:
            set_cookie = response.headers.get('Set-Cookie', '')
            new_tokens = re.findall(r'([a-zA-Z0-9_-]+)=[^;]+', set_cookie)
            cookie_dict = dict(re.findall(r'([a-zA-Z0-9_-]+)=([^;]+)', cookie))
            for token in new_tokens:
                if token not in cookie_dict:
                    cookie_dict[token] = ''
            return ';'.join(f'{k}={v}' for k, v in cookie_dict.items() if v)
    except:
        pass
    return cookie

def get_uid_fbdtsg(ck):
    try:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Connection': 'keep-alive',
            'Cookie': ck,
            'Host': 'www.facebook.com',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.get('https://www.facebook.com/', headers=headers)
            
            if response.status_code != 200:
                print(f"Status Code >> {response.status_code}")
                return None, None, None, None, None, None
                
            html_content = response.text
            
            user_id = None
            fb_dtsg = None
            jazoest = None
            
            script_tags = re.findall(r'<script id="__eqmc" type="application/json[^>]*>(.*?)</script>', html_content)
            for script in script_tags:
                try:
                    json_data = json.loads(script)
                    if 'u' in json_data:
                        user_param = re.search(r'__user=(\d+)', json_data['u'])
                        if user_param:
                            user_id = user_param.group(1)
                            break
                except:
                    continue
            
            fb_dtsg_match = re.search(r'"f":"([^"]+)"', html_content)
            if fb_dtsg_match:
                fb_dtsg = fb_dtsg_match.group(1)
            
            jazoest_match = re.search(r'jazoest=(\d+)', html_content)
            if jazoest_match:
                jazoest = jazoest_match.group(1)
            
            revision_match = re.search(r'"server_revision":(\d+),"client_revision":(\d+)', html_content)
            rev = revision_match.group(1) if revision_match else ""
            
            a_match = re.search(r'__a=(\d+)', html_content)
            a = a_match.group(1) if a_match else "1"
            
            req = "1b"
                
            return user_id, fb_dtsg, rev, req, a, jazoest
                
        except requests.exceptions.RequestException as e:
            print(f"Lỗi Kết Nối Khi Lấy UID/FB_DTSG: {e}")
            return get_uid_fbdtsg(ck)
            
    except Exception as e:
        print(f"Lỗi: {e}")
        return None, None, None, None, None, None

def get_info(uid: str, cookie: str, fb_dtsg: str, a: str, req: str, rev: str) -> Dict[str, Any]:
    try:
        form = {
            "ids[0]": uid,
            "fb_dtsg": fb_dtsg,
            "__a": a,
            "__req": req,
            "__rev": rev
        }
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookie,
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        response = requests.post(
            "https://www.facebook.com/chat/user_info/",
            headers=headers,
            data=form
        )
        
        if response.status_code != 200:
            return {"error": f"Lỗi Kết Nối: {response.status_code}"}
        
        try:
            text_response = response.text
            if text_response.startswith("for (;;);"):
                text_response = text_response[9:]
            
            res_data = json.loads(text_response)
            
            if "error" in res_data:
                return {"error": res_data.get("error")}
            
            if "payload" in res_data and "profiles" in res_data["payload"]:
                return format_data(res_data["payload"]["profiles"])
            else:
                return {"error": f"Không Tìm Thấy Thông Tin Của {uid}"}
                
        except json.JSONDecodeError:
            return {"error": "Lỗi Khi Phân Tích JSON"}
            
    except Exception as e:
        print(f"Lỗi Khi Get Info: {e}")
        return {"error": str(e)}

def format_data(profiles):
    if not profiles:
        return {"error": "Không Có Data"}
    
    first_profile_id = next(iter(profiles))
    profile = profiles[first_profile_id]
    
    return {
        "id": first_profile_id,
        "name": profile.get("name", ""),
        "url": profile.get("url", ""),
        "thumbSrc": profile.get("thumbSrc", ""),
        "gender": profile.get("gender", "")
    }

def cmt_gr_pst(cookie, grid, postIDD, ctn, user_id, fb_dtsg, rev, req, a, jazoest, uidtag=None, nametag=None):
    try:
        if not all([user_id, fb_dtsg, jazoest]):
            print("Thiếu user_id, fb_dtsg hoặc jazoest")
            return False
            
        pstid_enc = base64.b64encode(f"feedback:{postIDD}".encode()).decode()
        
        client_mutation_id = str(round(random.random() * 19))
        session_id = get_guid()  
        crt_time = int(time.time() * 1000)
        
        variables = {
            "feedLocation": "DEDICATED_COMMENTING_SURFACE",
            "feedbackSource": 110,
            "groupID": grid,
            "input": {
                "client_mutation_id": client_mutation_id,
                "actor_id": user_id,
                "attachments": None,
                "feedback_id": pstid_enc,
                "formatting_style": None,
                "message": {
                    "ranges": [],
                    "text": ctn
                },
                "attribution_id_v2": f"SearchCometGlobalSearchDefaultTabRoot.react,comet.search_results.default_tab,tap_search_bar,{crt_time},775647,391724414624676,,",
                "vod_video_timestamp": None,
                "is_tracking_encrypted": True,
                "tracking": [],
                "feedback_source": "DEDICATED_COMMENTING_SURFACE",
                "session_id": session_id
            },
            "inviteShortLinkKey": None,
            "renderLocation": None,
            "scale": 3,
            "useDefaultActor": False,
            "focusCommentID": None,
            "__relay_internal__pv__IsWorkUserrelayprovider": False
        }
        
        if uidtag and nametag:
            name_position = ctn.find(nametag)
            if name_position != -1:
                variables["input"]["message"]["ranges"] = [
                    {
                        "entity": {
                            "id": uidtag
                        },
                        "length": len(nametag),
                        "offset": name_position
                    }
                ]
            
        payload = {
            'av': user_id,
            '__crn': 'comet.fbweb.CometGroupDiscussionRoute',
            'fb_dtsg': fb_dtsg,
            'jazoest': jazoest,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'useCometUFICreateCommentMutation',
            'variables': json.dumps(variables),
            'server_timestamps': 'true',
            'doc_id': '24323081780615819'
        }
        
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookie,
            'Origin': 'https://www.facebook.com',
            'Referer': f'https://www.facebook.com/groups/{grid}',
            'User-Agent': 'python-http/0.27.0'
        }
        
        response = requests.post('https://www.facebook.com/api/graphql', data=payload, headers=headers)
        print(f"Mã trạng thái cho bài {postIDD}: {response.status_code}")
        print(f"Phản hồi: {response.text[:500]}...")  
        
        if response.status_code == 200:
            try:
                json_response = response.json()
                if 'errors' in json_response:
                    print(f"Lỗi GraphQL: {json_response['errors']}")
                    return False
                if 'data' in json_response and 'comment_create' in json_response['data']:
                    print("Bình luận đã được đăng")
                    return True
                print("Không tìm thấy comment_create trong phản hồi")
                return False
            except ValueError:
                print("Phản hồi JSON không hợp lệ")
                return False
        else:
            return False
    except Exception as e:
        print(f"Lỗi khi gửi bình luận: {e}")
        return False

def extract_post_group_id(post_link):
    post_match = re.search(r'facebook\.com/.+/permalink/(\d+)', post_link)
    group_match = re.search(r'facebook\.com/groups/(\d+)', post_link)
    if not post_match or not group_match:
        return None, None
    return post_match.group(1), group_match.group(1)
 
@tree.command(name="nhaynamebox", description="Treo đổi tên box Messenger theo file nhay.txt")
@app_commands.describe(
    cookie="Cookie Facebook",
    box_id="ID hộp chat (thread ID)",
    delay="Delay giữa mỗi lần đổi tên (giây)"
)
async def nhaynamebox(
    interaction: discord.Interaction,
    cookie: str,
    box_id: str,
    delay: float
):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    # Defer ngay để tránh lỗi interaction timeout
    await interaction.response.defer(thinking=True)

    # Đọc file nhay.txt
    try:
        with open("nhay.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return await interaction.followup.send("❌ Không tìm thấy file `nhay.txt`!")

    if not lines:
        return await interaction.followup.send("❌ File `nhay.txt` không có nội dung!")

    try:
        from toolnamebox import dataGetHome, tenbox
    except ImportError:
        return await interaction.followup.send("❌ Không thể import module `toolnamebox`!")

    dataFB = dataGetHome(cookie)
    stop_event = threading.Event()
    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    # Worker spam đổi tên liên tục
    def nhayname_worker():
        index = 0
        while not stop_event.is_set():
            new_title = lines[index % len(lines)]
            index += 1

            success, log = tenbox(new_title, box_id, dataFB)
            print(log)

            for _ in range(int(delay)):
                if stop_event.is_set():
                    return
                time.sleep(1)
            if stop_event.is_set():
                return
            time.sleep(delay - int(delay))

    # Tạo thread riêng cho mỗi user
    th = threading.Thread(target=nhayname_worker, daemon=True)

    with NHAYNAMEBOX_LOCK:
        if discord_user_id not in user_nhaynamebox_tabs:
            user_nhaynamebox_tabs[discord_user_id] = []
        user_nhaynamebox_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "box_id": box_id,
            "delay": delay
        })

    th.start()

    await interaction.followup.send(
        f"✅ Đã bắt đầu spam đổi tên box Messenger cho <@{discord_user_id}>:\n"
        f"• BoxID: `{box_id}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Số dòng tên: `{len(lines)}`\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
@tree.command(name="tabnhaynamebox", description="Quản lý/dừng tab đổi tên box Messenger")
async def tabnhaynamebox(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    discord_user_id = str(interaction.user.id)
    with NHAYNAMEBOX_LOCK:
        tabs = user_nhaynamebox_tabs.get(discord_user_id, [])

    if not tabs:
        return await safe_send(interaction, "❌ Bạn không có tab đổi tên nào đang hoạt động.")

    msg = "**Danh sách tab đổi tên box của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        msg += f"{idx}. BoxID: `{tab['box_id']}` | Delay: `{tab['delay']}`s | Uptime: `{uptime}`\n"
    msg += "\n➡️ Nhập số thứ tự của tab bạn muốn **dừng**."

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱️ Hết thời gian. Không dừng tab nào.")

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("⚠️ Không hợp lệ. Không dừng tab nào.")
    i = int(c)
    if not (1 <= i <= len(tabs)):
        return await interaction.followup.send("⚠️ Số không hợp lệ.")

    with NHAYNAMEBOX_LOCK:
        chosen = tabs.pop(i - 1)
        chosen["stop_event"].set()
        if not tabs:
            del user_nhaynamebox_tabs[discord_user_id]

    await interaction.followup.send(f"⛔ Đã dừng tab đổi tên số `{i}`")

class Mention:
    thread_id = None
    offset = None
    length = None

    def __init__(self, thread_id, offset, length):
        self.thread_id = thread_id
        self.offset = offset
        self.length = length

    @classmethod
    def _from_range(cls, data):
        return cls(
            thread_id=data["entity"].get("id"),
            offset=data["offset"],
            length=data["length"],
        )

    @classmethod
    def _from_prng(cls, data):
        return cls(thread_id=data["i"], offset=data["o"], length=data["l"])

    def _to_send_data(self, i):
        return {
            f"profile_xmd[{i}][id]": self.thread_id,
            f"profile_xmd[{i}][offset]": self.offset,
            f"profile_xmd[{i}][length]": self.length,
            f"profile_xmd[{i}][type]": "p",
        }

def get_auth_tokens(ck):
    try:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Connection': 'keep-alive',
            'Cookie': ck,
            'Host': 'www.facebook.com',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }

        response = requests.get('https://www.facebook.com/', headers=headers)

        if response.status_code != 200:
            return None, None, None, None, None, None

        html = response.text

        user_id = re.search(r'"USER_ID":"(\d+)"', html)
        user_id = user_id.group(1) if user_id else None

        fb_dtsg = re.search(r'\["DTSGInitData",\[],{"token":"(.*?)"}', html)
        fb_dtsg = fb_dtsg.group(1) if fb_dtsg else None

        rev = re.search(r'"client_revision":(\d+),', html)
        rev = rev.group(1) if rev else None

        a = "1"
        req = "1b"
        jazoest = re.search(r'name="jazoest" value="(\d+)"', html)
        jazoest = jazoest.group(1) if jazoest else "265817"

        return user_id, fb_dtsg, rev, req, a, jazoest
    except Exception as e:
        print(f"Lỗi get_auth_tokens: {e}")
        return None, None, None, None, None, None

def fetch_user_info(uid: str, cookie: str) -> Dict[str, Any]:
    try:
        user_id, fb_dtsg, rev, req, a, jazoest = get_auth_tokens(cookie)
        
        if not all([user_id, fb_dtsg]):
            return {"error": "Không thể lấy thông tin xác thực. Cookie có thể đã hết hạn."}
        
        form = {
            "ids[0]": uid,
            "fb_dtsg": fb_dtsg,
            "__a": a,
            "__req": req,
            "__rev": rev
        }
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookie,
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        response = requests.post(
            "https://www.facebook.com/chat/user_info/",
            headers=headers,
            data=form
        )
        
        if response.status_code != 200:
            return {"error": f"Lỗi kết nối: {response.status_code}"}
        
        try:
            text_response = response.text
            if text_response.startswith("for (;;);"):
                text_response = text_response[9:]
            
            res_data = json.loads(text_response)
            
            if "error" in res_data:
                return {"error": res_data.get("error")}
            
            if "payload" in res_data and "profiles" in res_data["payload"]:
                return format_data(res_data["payload"]["profiles"])
            else:
                return {"error": "Không tìm thấy thông tin người dùng"}
                
        except json.JSONDecodeError:
            return {"error": "Lỗi khi phân tích dữ liệu JSON"}
            
    except Exception as e:
        print(f"Lỗi fetch_user_info: {e}")
        return {"error": str(e)}

def format_data(profiles):
    if not profiles:
        return {"error": "Không Có Data"}
    
    first_profile_id = next(iter(profiles))
    profile = profiles[first_profile_id]
    
    return {
        "id": first_profile_id,
        "name": profile.get("name", ""),
        "url": profile.get("url", ""),
        "thumbSrc": profile.get("thumbSrc", ""),
        "gender": profile.get("gender", "")
    }

def send_messages(user_id, fb_dtsg, rev, req, a, ck, idbox, uid, name, delay):
    if not os.path.exists("nhay1.txt"):
        print("❌ Không tìm thấy file nhay.txt")
        return

    with open("nhay1.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Cookie': ck,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.facebook.com',
        'Referer': f'https://www.facebook.com/messages/t/{idbox}'
    }

    count = 0
    while True:
        for line in lines:
            tag_name = f"@{name}"
            if random.choice([True, False]):
                body = f"{tag_name} {line}"
                offset = 0
            else:
                body = f"{line} {tag_name}"
                offset = len(line) + 1

            mention = Mention(thread_id=uid, offset=offset, length=len(tag_name))
            ts = str(int(time.time() * 1000))

            payload = {
                "thread_fbid": idbox,
                "action_type": "ma-type:user-generated-message",
                "body": body,
                "client": "mercury",
                "author": f"fbid:{user_id}",
                "timestamp": ts,
                "offline_threading_id": ts,
                "message_id": ts,
                "source": "source:chat:web",
                "ephemeral_ttl_mode": "0",
                "__user": user_id,
                "__a": a,
                "__req": req,
                "__rev": rev,
                "fb_dtsg": fb_dtsg,
                "source_tags[0]": "source:chat"
            }

            payload.update(mention._to_send_data(0))

            try:
                response = requests.post("https://www.facebook.com/messaging/send/", headers=headers, data=payload)
                if response.status_code == 200:
                    count += 1
                    print(f"[✔] Đã gửi ({count}): {body}")
                else:
                    print(f"[✘] Lỗi ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"Lỗi gửi tin nhắn: {e}")

            time.sleep(delay)
                    

# ==== MODAL NHẬP THÔNG TIN ====
class NhayTagModal(discord.ui.Modal, title="Điền thông tin"):
    cookie = discord.ui.TextInput(
        label="Cookie Facebook", 
        style=discord.TextStyle.paragraph, 
        required=True
    )
    idbox = discord.ui.TextInput(
        label="ID Box / Chat 1-1", 
        required=True
    )
    uidtag = discord.ui.TextInput(
        label="UID tag", 
        placeholder="Nhập nhiều UID, cách nhau bằng dấu phẩy (tùy chọn)", 
        required=False
    )
    delay = discord.ui.TextInput(
        label="Delay (giây)", 
        required=True, 
        placeholder="Ví dụ: 2"
    )

    def __init__(self, interaction: discord.Interaction):
        super().__init__()
        self.interaction = interaction

async def on_submit(self, interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)  # tránh lỗi Unknown interaction

    cookie = self.cookie.value
    idbox = self.idbox.value
    uidtag = self.uidtag.value
    delay = float(self.delay.value)

    # ✅ Check quyền
    if not is_admin(self.interaction.user.id):
        embed_no_perm = discord.Embed(
            title="❌ Không có quyền",
            description="Bạn không có quyền dùng lệnh này",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=embed_no_perm)

    # Đọc file nội dung spam
    try:
        with open("nhay1.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        embed_file_err = discord.Embed(
            title="❌ File không tìm thấy",
            description="Không tìm thấy file `nhay1.txt`",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=embed_file_err)

    if not lines:
        embed_empty = discord.Embed(
            title="❌ File rỗng",
            description="File `nhay1.txt` không có nội dung!",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=embed_empty)

    # Lấy token auth từ cookie
    try:
        user_id, fb_dtsg, rev, req, a, jazoest = get_auth_tokens(cookie)
    except Exception as e:
        embed_auth_err = discord.Embed(
            title="❌ Lỗi lấy token Facebook",
            description=str(e),
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=embed_auth_err)

    if not all([user_id, fb_dtsg]):
        embed_invalid_cookie = discord.Embed(
            title="❌ Cookie không hợp lệ",
            description="Cookie không hợp lệ hoặc đã hết hạn.",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=embed_invalid_cookie)

    # Nếu có UID tag thì fetch thông tin
    uid_list = [u.strip() for u in uidtag.split(",") if u.strip()]
    user_infos = {}
    for u in uid_list:
        info = fetch_user_info(u, cookie)
        if "error" in info:
            embed_fetch_err = discord.Embed(
                title="❌ Lỗi fetch UID",
                description=info["error"],
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=embed_fetch_err)
        user_infos[u] = info.get("name", "Người dùng")

    stop_event = threading.Event()
    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    # Worker spam
    def nhaytag_worker():
        count = 0
        while not stop_event.is_set():
            for line in lines:
                if stop_event.is_set():
                    break

                body = line
                mentions = {}
                offset = len(body)

                # Thêm mention
                for uid in uid_list:
                    tag_name = user_infos[uid]
                    body += f" @{tag_name}"
                    mentions[uid] = (offset, len(tag_name))
                    offset += len(tag_name) + 2

                ts = str(int(time.time() * 1000))
                payload = {
                    "thread_fbid": idbox,
                    "action_type": "ma-type:user-generated-message",
                    "body": body,
                    "client": "mercury",
                    "author": f"fbid:{user_id}",
                    "timestamp": ts,
                    "offline_threading_id": ts,
                    "message_id": ts,
                    "source": "source:chat:web",
                    "ephemeral_ttl_mode": "0",
                    "__user": user_id,
                    "__a": a,
                    "__req": req,
                    "__rev": rev,
                    "fb_dtsg": fb_dtsg,
                    "source_tags[0]": "source:chat"
                }

                idx = 0
                for uid, (start, length) in mentions.items():
                    mention = Mention(thread_id=uid, offset=start, length=length)
                    payload.update(mention._to_send_data(idx))
                    idx += 1

                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Cookie': cookie,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://www.facebook.com',
                    'Referer': f'https://www.facebook.com/messages/t/{idbox}'
                }

                try:
                    res = requests.post("https://www.facebook.com/messaging/send/", headers=headers, data=payload)
                    if res.status_code == 200:
                        count += 1
                        print(f"[✓] Gửi #{count}: {body}")
                    else:
                        print(f"[×] Lỗi ({res.status_code})")
                except Exception as e:
                    print(f"[!] Lỗi gửi: {e}")

                # Delay
                for _ in range(int(delay)):
                    if stop_event.is_set():
                        return
                    time.sleep(1)
                if stop_event.is_set():
                    return
                time.sleep(delay - int(delay))

    th = threading.Thread(target=nhaytag_worker, daemon=True)

    with NHAYTAG_LOCK:
        if discord_user_id not in user_nhaytag_tabs:
            user_nhaytag_tabs[discord_user_id] = []
        user_nhaytag_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "idbox": idbox,
            "uid": uid_list,
            "delay": delay
        })

    th.start()

    # Embed báo task
    embed = discord.Embed(
        title="✅ Đã bắt đầu spam mess",
        description=f"Task spam của <@{discord_user_id}> đã được khởi tạo.",
        color=discord.Color.green(),
        timestamp=start_time
    )
    embed.add_field(name="• Box/Chat", value=idbox, inline=True)
    embed.add_field(name="• Số UID tag", value=len(uid_list), inline=True)
    embed.add_field(name="• Delay", value=f"{delay} giây", inline=True)
    embed.set_footer(text="Bắt đầu lúc")

    await interaction.followup.send(embed=embed)



# ==== VIEW NÚT ====
class NhayTagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.secondary, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NhayTagModal(interaction))


# ==== LỆNH /NHAYTAGMESS ====
admin_id = 1310263571434704988

@tree.command(name="nhaytagmess", description="Spam Messenger có thể tag nhiều UID hoặc chat riêng 1-1")
async def nhaytagmess(interaction: discord.Interaction):
    # ==== CHECK QUYỀN ====
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description=f"Bạn không có quyền sử dụng lệnh này, vui lòng liên hệ <@{admin_id}>.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    embed = discord.Embed(
        title="📢 Nhây Tag Messenger VIP",
        description=(
            "Ấn vào nút để bắt đầu điền thông tin"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Nhây Messenger đa tag độc quyền by ManhBui")

    view = NhayTagView()
    await interaction.response.send_message(embed=embed, view=view)
    

@tree.command(name="tabnhaytagmess", description="Quản lý/dừng tab spam tag Messenger")
async def tabnhaytagmess(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    discord_user_id = str(interaction.user.id)
    with NHAYTAG_LOCK:
        tabs = user_nhaytag_tabs.get(discord_user_id, [])

    if not tabs:
        embed = discord.Embed(
            title="❌ Không có tab nhây tag mess nào đang chạy",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    # Embed danh sách tab
    embed = discord.Embed(
        title="📋 Danh sách tab spam tag đang chạy",
        description="Nhập **số thứ tự** để dừng tab.\nNhập `All` để **dừng tất cả tab**.",
        color=discord.Color.blurple()
    )

    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        embed.add_field(
            name=f"Tab #{idx}",
            value=(
                f"**Box:** `{tab['idbox']}`\n"
                f"**UID tag:** `{tab['uid']}`\n"
                f"**Delay:** `{tab['delay']}s`\n"
                f"**Uptime:** `{uptime}`"
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏱️ Hết thời gian",
            description="Không dừng tab nào.",
            color=discord.Color.orange()
        )
        return await interaction.followup.send(embed=timeout_embed)

    c = reply.content.strip()

    # Trường hợp dừng tất cả
    if c.lower() == "all":
        with NHAYTAG_LOCK:
            for tab in list(tabs):
                tab["stop_event"].set()
            user_nhaytag_tabs.pop(discord_user_id, None)

        done_embed = discord.Embed(
            title="⛔ Đã dừng tất cả tab nhây tag",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=done_embed)

    # Trường hợp dừng 1 tab
    if not c.isdigit():
        invalid_embed = discord.Embed(
            title="⚠️ Không hợp lệ",
            description="Bạn cần nhập số thứ tự hoặc `All`.",
            color=discord.Color.orange()
        )
        return await interaction.followup.send(embed=invalid_embed)

    i = int(c)
    if not (1 <= i <= len(tabs)):
        invalid_num_embed = discord.Embed(
            title="⚠️ Số không hợp lệ",
            description="Vui lòng nhập đúng số thứ tự trong danh sách.",
            color=discord.Color.orange()
        )
        return await interaction.followup.send(embed=invalid_num_embed)

    with NHAYTAG_LOCK:
        chosen = tabs.pop(i - 1)
        chosen["stop_event"].set()
        if not tabs:
            del user_nhaytag_tabs[discord_user_id]

    done_one_embed = discord.Embed(
        title="⛔ Đã dừng tab spam tag",
        description=f"Đã dừng tab số `{i}` thành công.",
        color=discord.Color.red()
    )
    await interaction.followup.send(embed=done_one_embed)
                                                                                                                                    
@tree.command(
    name="tabnhaytop",
    description="Quản lý/dừng tab nhây top"
)
async def tabnhaytop(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")

    discord_user_id = str(interaction.user.id)
    with NHAY_LOCK:
        tabs = user_nhay_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab nhây top nào đang hoạt động")

    msg = "**Danh sách tab nhây top của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        msg += (
            f"{idx}. Group:`{tab['group_id']}` Post:`{tab['post_id']}` | "
            f"Delay:`{tab['delay']}`s | Uptime:`{uptime}`\n"
        )
    msg += "\nNhập số tab để dừng tab".format(len(tabs))
    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào")

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("Không dừng tab nào")
    i = int(c)
    if not (1 <= i <= len(tabs)):
        return await interaction.followup.send("Số không hợp lệ")

    with NHAY_LOCK:
        chosen = tabs.pop(i-1)
        chosen["stop_event"].set()
        if not tabs:
            del user_nhay_tabs[discord_user_id]

    await interaction.followup.send(f"Đã dừng tab nhây số {i}")   
    
def telegram_send_loop(token, chat_ids, caption, photo, delay, stop_event, discord_user_id):
    while not stop_event.is_set():
        for chat_id in chat_ids:
            if stop_event.is_set():
                break
            try:
                if photo:
                    if photo.startswith("http"):
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        data = {"chat_id": chat_id, "caption": caption, "photo": photo}
                        resp = requests.post(url, data=data, timeout=10)
                    else:
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        with open(photo, "rb") as f:
                            files = {"photo": f}
                            data = {"chat_id": chat_id, "caption": caption}
                            resp = requests.post(url, data=data, files=files, timeout=10)
                else:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    data = {"chat_id": chat_id, "text": caption}
                    resp = requests.post(url, data=data, timeout=10)

                if resp.status_code == 200:
                    print(f"[TELE][{discord_user_id}] {token[:10]}... → {chat_id}")
                elif resp.status_code == 429:
                    retry = resp.json().get("parameters", {}).get("retry_after", 10)
                    print(f"[TELE][{discord_user_id}] Rate limit {retry}s")
                    time.sleep(retry)
                else:
                    print(f"[TELE][{discord_user_id}] Err {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                print(f"[TELE][{discord_user_id}] Conn Err: {e}")
            time.sleep(0.2)
        time.sleep(delay)           

def _ig_spam_loop(task_id, discord_user_id):
    with IG_LOCK:
        task = next((t for t in SPAM_TASKS[discord_user_id] if t["id"] == task_id), None)
    if not task:
        return

    cl       = task["client"]
    targets  = task["targets"]
    message  = task["message"]
    delay    = task["delay"]
    stop_set = task["stop_targets"]

    while True:
        for target in targets:
            if target in stop_set:
                continue
            try:
                if target.isdigit():
                    cl.direct_send(message, thread_ids=[target])
                else:
                    uid = cl.user_id_from_username(target)
                    cl.direct_send(message, thread_ids=[uid])
                print(f"[IG][{discord_user_id}] Gửi tới {target}")
            except Exception as e:
                print(f"[IG][{discord_user_id}] Lỗi {target}: {e}")
        time.sleep(delay)           

def parse_gmail_accounts(input_str: str):
    accounts = []
    for entry in re.split(r"[,/]", input_str):
        if "|" in entry:
            email, pwd = entry.split("|",1)
            accounts.append({
                "server": "smtp.gmail.com",
                "port": 465,
                "email": email.strip(),
                "password": pwd.strip(),
                "active": True
            })
    return accounts

def send_mail(smtp_info, to_email, content):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_info["server"], smtp_info["port"], context=context) as server:
        server.login(smtp_info["email"], smtp_info["password"])
        msg = MIMEText(content)
        msg["From"] = smtp_info["email"]
        msg["To"] = to_email
        msg["Subject"] = " "
        server.sendmail(smtp_info["email"], to_email, msg.as_string())

def gmail_spam_loop(tab, discord_user_id):
    smtp_list = tab["smtp_list"]
    to_email  = tab["to_email"]
    content   = tab["content"]
    delay     = tab["delay"]
    stop_evt  = tab["stop_event"]
    idx = 0
    while not stop_evt.is_set():
        active = [acc for acc in smtp_list if acc["active"]]
        if not active:
            for acc in smtp_list: acc["active"] = True
            active = smtp_list
        smtp = active[idx % len(active)]
        try:
            send_mail(smtp, to_email, content)
            print(f"[GMAIL][{discord_user_id}] ✓ {smtp['email']} → {to_email}")
        except smtplib.SMTPAuthenticationError:
            smtp["active"] = False
            print(f"[GMAIL][{discord_user_id}] ✗ Auth failed {smtp['email']}")
        except smtplib.SMTPDataError as e:
            txt = str(e)
            if "Quota" in txt or "limit" in txt:
                smtp["active"] = False
                print(f"[GMAIL][{discord_user_id}] Quota limit {smtp['email']}")
            else:
                print(f"[GMAIL][{discord_user_id}] DataErr {smtp['email']}: {e}")
        except Exception as e:
            print(f"[GMAIL][{discord_user_id}] Err {smtp['email']}: {e}")
        idx += 1
        for _ in range(int(delay)):
            if stop_evt.is_set(): break
            time.sleep(1)
        if stop_evt.is_set(): break
        time.sleep(delay - int(delay))      
                   
def get_uptime(start_time: datetime) -> str:
    elapsed = (datetime.now() - start_time).total_seconds()
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

@tasks.loop(minutes=60)
async def cleanup_expired_users():
    users = load_users()
    to_remove = []
    for uid, exp in users.items():
        if exp and datetime.fromisoformat(exp) <= datetime.now():
            to_remove.append(uid)
    if to_remove:
        for uid in to_remove:
            _remove_user_and_kill_tabs(uid)

class Kem:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = self.id_user()
        self.fb_dtsg = None
        self.init_params()

    def id_user(self):
        try:
            c_user = re.search(r"c_user=(\d+)", self.cookie).group(1)
            return c_user
        except:
            raise Exception("Cookie không hợp lệ")

    def init_params(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
        }
        try:
            response = requests.get('https://www.facebook.com', headers=headers)
            fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
            if not fb_dtsg_match:
                response = requests.get('https://mbasic.facebook.com', headers=headers)
                fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
                if not fb_dtsg_match:
                    response = requests.get('https://m.facebook.com', headers=headers)
                    fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
            if fb_dtsg_match:
                self.fb_dtsg = fb_dtsg_match.group(1)
            else:
                raise Exception("Không thể lấy được fb_dtsg")
        except Exception as e:
            raise Exception(f"Lỗi khi khởi tạo tham số: {str(e)}")

    def gui_tn(self, recipient_id, message):
        if not message or not recipient_id:
            raise ValueError("ID Box và Nội Dung không được để trống")
        timestamp = int(time.time() * 1000)
        data = {
            'thread_fbid': recipient_id,
            'action_type': 'ma-type:user-generated-message',
            'body': message,
            'client': 'mercury',
            'author': f'fbid:{self.user_id}',
            'timestamp': timestamp,
            'source': 'source:chat:web',
            'offline_threading_id': str(timestamp),
            'message_id': str(timestamp),
            'ephemeral_ttl_mode': '',
            '__user': self.user_id,
            '__a': '1',
            '__req': '1b',
            '__rev': '1015919737',
            'fb_dtsg': self.fb_dtsg
        }
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'python-http/0.27.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers)
            if response.status_code != 200:
                return {'success': False, 'error_description': f'Status: {response.status_code}'}
            if 'for (;;);' in response.text:
                clean = response.text.replace('for (;;);', '')
                result = json.loads(clean)
                if 'error' in result:
                    return {'success': False, 'error_description': result.get('errorDescription', 'Unknown error')}
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error_description': str(e)}

def spam_tab_worker(messenger: Kem, box_id: str, get_message_func, delay: float, stop_event: threading.Event, start_time: datetime, discord_user_id: str):
    success = 0
    fail = 0

    while not stop_event.is_set():
        message = get_message_func()
        result = messenger.gui_tn(box_id, message)
        ok = result.get("success", False)
        if ok:
            success += 1
            status = "OK"
        else:
            fail += 1
            status = f"FAIL: {result.get('error_description', 'Unknown error')}"

        uptime = (datetime.now() - start_time).total_seconds()
        h, rem = divmod(int(uptime), 3600)
        m, s = divmod(rem, 60)
        print(f"[{messenger.user_id}] → {box_id} | {status} | Up: {h:02}:{m:02}:{s:02} | OK: {success} | FAIL: {fail}".ljust(120), end='\r')

        time.sleep(delay)
        gc.collect()

    print(f"\nTab của user {discord_user_id} với cookie {messenger.user_id} đã dừng.")

                        
                    

# ==== TREO MESS (TEXT) ====
class TreoMessModal(discord.ui.Modal, title="Treo Messenger (Text)"):
    cookie = discord.ui.TextInput(label="Cookie Facebook", placeholder="Nhập cookie...")
    box_id = discord.ui.TextInput(label="ID Box", placeholder="Nhập ID box ...")
    content = discord.ui.TextInput(label="Nội dung spam", style=discord.TextStyle.paragraph)
    delay = discord.ui.TextInput(label="Delay (giây)", placeholder="VD: 20")

    async def on_submit(self, interaction: discord.Interaction):
        if not has_permission(interaction):
            return await interaction.response.send_message("Bạn không có quyền dùng lệnh này", ephemeral=True)

        cookie = self.cookie.value.strip()
        box_id = self.box_id.value.strip()
        content = self.content.value.strip()
        try:
            delay = float(self.delay.value.strip())
        except:
            return await interaction.response.send_message("❌ Delay không hợp lệ!", ephemeral=True)

        try:
            messenger = Kem(cookie)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Cookie không hợp lệ hoặc lỗi: {e}", ephemeral=True)

        def get_message():
            return content

        stop_event = threading.Event()
        start_time = datetime.now()
        discord_user_id = str(interaction.user.id)

        th = threading.Thread(
            target=spam_tab_worker,
            args=(messenger, box_id, get_message, delay, stop_event, start_time, discord_user_id),
            daemon=True
        )
        th.start()

        with TAB_LOCK:
            if discord_user_id not in user_tabs:
                user_tabs[discord_user_id] = []
            user_tabs[discord_user_id].append({
                "box_id": box_id,
                "delay": delay,
                "start": start_time,
                "stop_event": stop_event,
                "type": "text",
                "content": content[:50]
            })

        await interaction.response.send_message(
            f"✅ Đã bắt đầu spam Messenger:\n"
            f"• Box: `{box_id}`\n"
            f"• Delay: `{delay}` giây\n"
            f"• Nội dung: ```{content[:50]}...```\n"
            f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
        )


# ==== VIEW ====
class TreoMessView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Bắt đầu", style=discord.ButtonStyle.green)
    async def text_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TreoMessModal())


# ==== LỆNH MỞ TREO MESS ====
@tree.command(name="treomess", description="Treo Messenger")
async def treomess(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền dùng lệnh này", ephemeral=True)

    embed = discord.Embed(
        title="📨 Treo Messenger",
        description="Ấn nút bên dưới để treo tin nhắn.",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed, view=TreoMessView())



@tree.command(name="tabtreomess", description="Quản lý/dừng tab treo Messenger")
async def tabtreomess(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description="Bạn không có quyền sử dụng bot.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    discord_user_id = str(interaction.user.id)
    with TAB_LOCK:
        tabs = user_tabs.get(discord_user_id, [])

    if not tabs:
        embed = discord.Embed(
            title="❌ Không có tab",
            description="Bạn không có tab treo Messenger nào đang hoạt động.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    # Embed danh sách tab
    embed = discord.Embed(
        title="📋 Danh sách tab treo Messenger",
        description="Nhập **số thứ tự** tab để dừng hoặc nhập `All` để dừng tất cả.",
        color=discord.Color.blurple()
    )

    for idx, tab in enumerate(tabs, start=1):
        uptime = get_uptime(tab["start"])
        embed.add_field(
            name=f"#{idx} | Delay: {tab['delay']}s",
            value=f"**Box:** `{tab['box_id']}`\n**Nội dung:** `{tab['content']}`\n🕒 Uptime: `{uptime}`",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏰ Hết thời gian",
            description="Bạn không nhập kịp, không có tab nào bị dừng.",
            color=discord.Color.orange()
        )
        return await interaction.followup.send(embed=timeout_embed)

    c = reply.content.strip()

    # Trường hợp dừng tất cả
    if c.lower() == "all":
        with TAB_LOCK:
            for tab in list(tabs):
                tab["stop_event"].set()
            user_tabs.pop(discord_user_id, None)

        done_all = discord.Embed(
            title="⛔ Đã dừng tất cả tab",
            description="Toàn bộ tab treo Messenger của bạn đã được dừng.",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=done_all)

    # Trường hợp dừng 1 tab
    if not c.isdigit():
        invalid = discord.Embed(
            title="⚠️ Không hợp lệ",
            description="Bạn cần nhập số thứ tự hoặc `All`.",
            color=discord.Color.yellow()
        )
        return await interaction.followup.send(embed=invalid)

    idx = int(c)
    if not (1 <= idx <= len(tabs)):
        invalid_num = discord.Embed(
            title="⚠️ Số không hợp lệ",
            description=f"Vui lòng nhập số từ 1 đến {len(tabs)}.",
            color=discord.Color.yellow()
        )
        return await interaction.followup.send(embed=invalid_num)

    with TAB_LOCK:
        chosen = tabs.pop(idx - 1)
        chosen["stop_event"].set()
        if not tabs:
            user_tabs.pop(discord_user_id, None)

    done_one = discord.Embed(
        title="✅ Đã dừng tab",
        description=f"Bạn đã dừng thành công **tab số {idx}**.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=done_one)


@tree.command(name="addadmin", description="Thêm user vào danh sách admin phụ")
@app_commands.describe(user="Tag hoặc ID user", thoihan="Thời hạn (ví dụ: 7d, bỏ trống = vĩnh viễn)")
async def addadmin(interaction: discord.Interaction, user: str, thoihan: str = None):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description="Bạn không có quyền sử dụng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    user_id = user.replace("<@", "").replace(">", "").replace("!", "")
    days = None
    if thoihan and thoihan.endswith("d"):
        try:
            days = int(thoihan[:-1])
        except:
            embed = discord.Embed(
                title="⚠️ Thời hạn không hợp lệ",
                description="Phải là số + 'd' (ví dụ: 7d).",
                color=discord.Color.yellow()
            )
            return await interaction.response.send_message(embed=embed)

    _add_user(user_id, days)
    embed = discord.Embed(
        title="✅ Đã thêm admin phụ",
        description=f"Đã thêm <@{user_id}> với quyền sử dụng bot "
                    f"{'vĩnh viễn' if not days else f'{days} ngày'}.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="xoaadmin", description="Xóa user khỏi danh sách admin phụ")
@app_commands.describe(user="Tag hoặc ID user")
async def xoaadmin(interaction: discord.Interaction, user: str):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description="Bạn không có quyền sử dụng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    user_id = user.replace("<@", "").replace(">", "").replace("!", "")
    _remove_user_and_kill_tabs(user_id)

    embed = discord.Embed(
        title="⛔ Đã xóa admin phụ",
        description=f"Đã xóa quyền sử dụng bot và dừng mọi tab của <@{user_id}>.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="listadmin", description="Hiển thị danh sách admin phụ hiện tại")
async def listadmin_cmd(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description="Bạn không có quyền sử dụng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    user_list = _get_user_list()
    if not user_list:
        embed = discord.Embed(
            title="📋 Danh sách admin phụ",
            description="Danh sách hiện đang rỗng.",
            color=discord.Color.orange()
        )
        return await interaction.response.send_message(embed=embed)

    await interaction.response.defer(thinking=True)

    embed = discord.Embed(
        title="📋 Danh sách admin phụ",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(
        url="https://media.discordapp.net/attachments/1389594739753484511/1411763880039944282/13474aab4bc986442fcbb22b1d7fda4e.jpg"
    )

    for index, (uid, time_str) in enumerate(user_list, start=1):
        try:
            user_obj = await bot.fetch_user(int(uid))
            name = f"{user_obj.name}#{user_obj.discriminator}"
            mention = user_obj.mention
        except Exception:
            name = f"Unknown User ({uid})"
            mention = f"<@{uid}>"

        embed.add_field(
            name=f"[{index}] 👤 {name}",
            value=f"🔗 {mention}\n⏳ Thời hạn: `{time_str}`",
            inline=False
        )

    await interaction.followup.send(embed=embed)

        
@tree.command(
    name="anhtop",
    description="Treo top ảnh kèm tag"
)
@app_commands.describe(
    link_post="Link bài viết",
    cookie="Cookie",
    message="Nội dung",
    images="Link ảnh",
    delay_min="Delay tối thiểu",
    delay_max="Delay tối đa",
    tag_id="ID cần tag"
)
async def anhtop(
    interaction: discord.Interaction,
    link_post: str,
    cookie: str,
    message: str,
    images: str,
    delay_min: float,
    delay_max: float,
    tag_id: str = None
):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")

    post_id = extract_facebook_post_id(link_post)
    if not post_id:
        return await interaction.response.send_message("Không thể lấy ID bài viết từ link")

    if not message.strip():
        return await interaction.response.send_message("Nội dung không được để trống")

    image_list = [img.strip() for img in images.split(",") if img.strip()]
    if not image_list:
        return await interaction.response.send_message("Phải có ít nhất 1 link ảnh")

    if delay_min <= 0 or delay_max <= 0 or delay_min > delay_max:
        return await interaction.response.send_message("Delay không hợp lệ (phải trên 0)")

    login = check_login_facebook(cookie)
    if not login:
        return await interaction.response.send_message("Cookie không hợp lệ")

    discord_user_id = str(interaction.user.id)
    stop_event = threading.Event()
    start_time = datetime.now()

    th = threading.Thread(
        target=image_tab_worker,
        args=(post_id, cookie, message, image_list, tag_id, delay_min, delay_max, stop_event, start_time, discord_user_id),
        daemon=True
    )
    th.start()

    with IMAGE_TAB_LOCK:
        if discord_user_id not in user_image_tabs:
            user_image_tabs[discord_user_id] = []
        user_image_tabs[discord_user_id].append({
            "post_id": post_id,
            "cookie": cookie,
            "message": message,
            "images": image_list,
            "tag_id": tag_id,
            "delay_min": delay_min,
            "delay_max": delay_max,
            "thread": th,
            "stop_event": stop_event,
            "start": start_time
        })

    await interaction.response.send_message(
        f"Đã khởi tạo tab ảnh top cho <@{discord_user_id}>:\n"
        f"• Post ID: `{post_id}`\n"
        f"• Delay: `{delay_min}–{delay_max}` giây\n"
        f"• Nội dung comment: `{message}`\n"
        f"• Số ảnh: `{len(image_list)}`\n"
        f"{'• Tag ID: ' + tag_id if tag_id else ''}\n"
        f"Thời gian bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
@tree.command(name="treoanhmess", description="Spam ảnh + tin nhắn Messenger liên tục")
@app_commands.describe(
    cookie="Cookie Facebook",
    box_id="ID hộp chat (thread ID)",
    image_link="Link ảnh jpg/png",
    message="Nội dung tin nhắn cần gửi (giữ nguyên dòng trắng, khoảng cách)",
    delay="Delay giữa các lần gửi (giây)"
)
async def treoanhmess(
    interaction: discord.Interaction,
    cookie: str,
    box_id: str,
    image_link: str,
    message: str,
    delay: float
):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    if delay < 1:
        return await safe_send(interaction, "Delay phải từ 1 giây trở lên.")

    stop_event = threading.Event()
    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    def treoanhmess_worker():
        try:
            from anhmess import NanhMessenger
            messenger = NanhMessenger(cookie)

            while not stop_event.is_set():
                image_id = messenger.up(image_link)
                if not image_id:
                    print("[×] Upload ảnh thất bại.")
                    continue

                result = messenger.gui_tn(box_id, message, image_id)
                if result.get("success"):
                    print("[✓] Gửi thành công.")
                else:
                    print("[×] Gửi thất bại.")

                for _ in range(int(delay)):
                    if stop_event.is_set(): break
                    time.sleep(1)
                if stop_event.is_set(): break
                time.sleep(delay - int(delay))
        except Exception as e:
            print(f"[LỖI] {e}")

    with IMAGE_TAB_LOCK:
        if discord_user_id not in user_image_tabs:
            user_image_tabs[discord_user_id] = []

        th = threading.Thread(target=treoanhmess_worker, daemon=True)
        user_image_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "box_id": box_id,
            "delay": delay,
            "message": message
        })
        th.start()

    await interaction.response.send_message(
        f"Đã tạo tab ảnh Messenger cho <@{discord_user_id}>:\n"
        f"• BoxID: `{box_id}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
@tree.command(name="tabanhmess", description="Quản lý/dừng tab ảnh Messenger đang chạy")
async def tabanhmess(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    discord_user_id = str(interaction.user.id)
    with IMAGE_TAB_LOCK:
        tabs = user_image_tabs.get(discord_user_id, [])

    if not tabs:
        return await safe_send(interaction, "Bạn không có tab ảnh Messenger nào đang hoạt động")

    msg = "**Danh sách tab ảnh Messenger của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        msg += (
            f"{idx}. BoxID: `{tab['box_id']}` | "
            f"Delay: `{tab['delay']}`s | Uptime: `{uptime}`\n"
        )
    msg += "\n➡️ Nhập số thứ tự của tab bạn muốn **dừng** (1 - {})".format(len(tabs))

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱️ Hết thời gian. Không dừng tab nào.")

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("⚠️ Không hợp lệ. Không dừng tab nào.")
    i = int(c)
    if not (1 <= i <= len(tabs)):
        return await interaction.followup.send("⚠️ Số không hợp lệ.")

    with IMAGE_TAB_LOCK:
        chosen = tabs.pop(i - 1)
        chosen["stop_event"].set()
        if not tabs:
            del user_image_tabs[discord_user_id]

    await interaction.followup.send(f"⛔ Đã dừng tab ảnh số `{i}`")            
@tree.command(name="listbox", description="Liệt kê toàn bộ box Messenger từ cookie")
@app_commands.describe(
    cookie="Cookie Facebook cần kiểm tra"
)
async def listbox(interaction: discord.Interaction, cookie: str):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    await interaction.response.send_message("🔍 Đang lấy danh sách box Messenger...")

    result = get_thread_list(cookie)

    if isinstance(result, dict) and "error" in result:
        return await interaction.followup.send(f"❌ {result['error']}")

    if not result:
        return await interaction.followup.send("❌ Không tìm thấy box nào.")

    CHUNK_SIZE = 30  # tối đa 30 box mỗi lần gửi
    chunks = [result[i:i + CHUNK_SIZE] for i in range(0, len(result), CHUNK_SIZE)]

    for idx, chunk in enumerate(chunks, 1):
        msg = f"📦 **Danh sách box ({(idx - 1) * CHUNK_SIZE + 1} - {min(idx * CHUNK_SIZE, len(result))})**\n"
        for i, thread in enumerate(chunk, start=(idx - 1) * CHUNK_SIZE + 1):
            name = thread['thread_name']
            tid = thread['thread_id']
            msg += f"{i}. {name} — `{tid}`\n"
        await interaction.followup.send(msg[:2000])
            
@tree.command(name="nhayzalo", description="Nhây zalo fake soạn")
@app_commands.describe(
    imei="IMEI Zalo",
    cookie="Cookie Zalo",
    delay="Delay giây",
    kieu="1=group, 2=1-1"
)
async def nhayzalo(interaction: discord.Interaction, imei: str, cookie: str, delay: float, kieu: int):
    if not has_permission(interaction):
        return await safe_send(interaction, "❌ Bạn không có quyền")

    if delay < 0.5:
        return await safe_send(interaction, "❌ Delay phải >= 0.5 giây")

    await interaction.response.send_message("⏳ Đang lấy danh sách...")

    try:
        cookies = json.loads(cookie)
        api = ZaloAPI(imei, cookies)
    except Exception as e:
        return await interaction.followup.send(f"❌ Lỗi khi khởi tạo API: {e}")

    if kieu == 1:
        danh_sach = api.fetch_groups()
        chon = "nhóm"
    elif kieu == 2:
        danh_sach = api.fetch_friends()
        chon = "người"
    else:
        return await interaction.followup.send("❌ Kiểu phải là 1 hoặc 2")

    if not danh_sach:
        return await interaction.followup.send(f"⚠️ Không tìm thấy {chon} nào.")

    msg = f"**Danh sách {chon}:**\n"
    for i, item in enumerate(danh_sach):
        msg += f"{i+1}. {item['name']} | ID: `{item['id']}`\n"
    msg += f"\nNhập STT các {chon} muốn spam (cách nhau bởi dấu phẩy):"

    chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("❌ Hết thời gian chọn")

    try:
        pick = [int(x.strip())-1 for x in reply.content.strip().split(",")]
        ids = [danh_sach[i]['id'] for i in pick if 0 <= i < len(danh_sach)]
    except:
        return await interaction.followup.send("❌ STT không hợp lệ!")

    try:
        with open("nhay.txt", "r", encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]
    except:
        return await interaction.followup.send("❌ Không tìm thấy file nhay.txt")

    if not messages:
        return await interaction.followup.send("❌ File nhay.txt trống")

    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    tool = SpamTool(
        name="ZaloBot",
        imei=imei,
        cookies=cookies,
        thread_ids=ids,
        thread_type=ThreadType.GROUP if kieu == 1 else ThreadType.USER,
        use_typing=True  # ✅ fake soạn
    )

    th = threading.Thread(target=tool.send_spam, args=(messages, delay), daemon=True)
    th.start()

    with NHAY_LOCK:
        if discord_user_id not in user_nhay_tabs:
            user_nhay_tabs[discord_user_id] = []
        user_nhay_tabs[discord_user_id].append({
            "tool": tool,
            "thread": th,
            "ids": ids,
            "kieu": kieu,
            "start": start_time,
            "delay": delay
        })

    await interaction.followup.send(
        f"✅ Đã bắt đầu tab nhayzalo | Kế: {'Nhóm' if kieu==1 else '1-1'}\n"
        f"Delay: `{delay}`s | ID: {', '.join(ids)}"
    )

@tree.command(name="tabnhayzalo", description="Quản lý/dừng tab nhây Zalo")
async def tabnhayzalo(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")

    discord_user_id = str(interaction.user.id)
    with NHAY_LOCK:
        tabs = user_nhay_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab nhây Zalo nào đang hoạt động")

    msg = "**Danh sách tab nhây Zalo của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        ids_str = ", ".join(tab["ids"])
        msg += (
            f"{idx}. Kiểu: `{'Nhóm' if tab['kieu']==1 else '1-1'}` | "
            f"Delay: `{tab['delay']}`s | ID: `{ids_str}` | "
            f"Uptime: `{uptime}`\n"
        )
    msg += "\nNhập số tab để dừng tab đó:"

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱ Hết thời gian chọn")

    content = reply.content.strip()
    if not content.isdigit():
        return await interaction.followup.send("❌ Không dừng tab nào")
    idx = int(content)
    if not (1 <= idx <= len(tabs)):
        return await interaction.followup.send("❌ Số không hợp lệ")

    with NHAY_LOCK:
        chosen = tabs.pop(idx - 1)
        # Cách nhẹ nhàng hơn: thêm flag trong SpamTool để dừng
        try:
            chosen["tool"].running = False
        except:
            pass
        if not tabs:
            del user_nhay_tabs[discord_user_id]

    await interaction.followup.send(f"✅ Đã dừng tab nhây Zalo số {idx}")        
    
   
@tree.command(
    name="tabanhtop",
    description="Quản lý/dừng tab treo ảnh top"
)
async def tabanhtop(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")

    discord_user_id = str(interaction.user.id)
    with IMAGE_TAB_LOCK:
        tabs = user_image_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab ảnh top nào đang hoạt động")

    msg = "**Danh sách tab ảnh top của bạn:**\n"
    for idx, tab in enumerate(tabs, start=1):
        uptime = get_uptime(tab["start"])
        msg += (
             f"{idx}. Post: `{tab['post_id']}` | Delay: `{tab['delay_min']}–{tab['delay_max']}` giây | "
             f"Uptime: `{uptime}` | Số ảnh: `{len(tab['images'])}`\n"
        )
    msg += "\nNhập số tab để dừng tab đó".format(len(tabs))

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return (
            m.author.id == interaction.user.id and 
            m.channel.id == interaction.channel.id
        )

    try:
        reply: discord.Message = await bot.wait_for("message", check=check, timeout=30.0)
        content = reply.content.strip()
        if content.isdigit():
            idx = int(content)
            if 1 <= idx <= len(tabs):
                with IMAGE_TAB_LOCK:
                    chosen = tabs[idx-1]
                    chosen["stop_event"].set()
                    tabs.pop(idx-1)
                    if not tabs:
                        del user_image_tabs[discord_user_id]
                return await interaction.followup.send(f"Đã dừng tab ảnh top số {idx}")
        await interaction.followup.send("Không dừng tab nào.")
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian (30s). Không dừng tab nào")

def parse_cookie_string(cookie_str):
    cookies = {}
    for part in cookie_str.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies
                            
@tree.command(
    name="treozalo",
    description="Treo ngôn Zalo (spam nhóm hoặc bạn bè)"
)
@app_commands.describe(
    imei="IMEI thiết bị Zalo",
    cookies="Cookie (JSON hoặc chuỗi key=value;...)",
    message="Nội dung cần spam",
    delay="Delay giữa mỗi tin (giây)"
)
async def treozalo(
    interaction: discord.Interaction,
    imei: str,
    cookies: str,
    message: str,
    delay: float
):
    if not has_permission(interaction):
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này")

    try:
        if cookies.strip().startswith("{"):
            cookies_dict = json.loads(cookies)
        else:
            cookies_dict = parse_cookie_string(cookies)
    except Exception as e:
        return await interaction.response.send_message(f"❌ Cookie không hợp lệ: {e}")

    if delay < 0.5:
        return await interaction.response.send_message("❌ Delay phải >= 0.5 giây.")

    # Gửi sớm để tránh timeout
    await interaction.response.send_message("📌 Chọn kiểu spam:\n`1` - Nhóm\n`2` - Bạn bè")

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply_type: discord.Message = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.channel.send("⏱ Hết thời gian chọn kiểu spam.")

    spam_type = reply_type.content.strip()
    if spam_type not in ["1", "2"]:
        return await interaction.channel.send("❌ Chỉ chọn `1` hoặc `2`.")

    try:
        api = ZaloAPI(imei, cookies_dict)
        if spam_type == "1":
            danh_sach = api.fetch_groups()
            label = "nhóm"
            thread_type = ThreadType.GROUP
        else:
            danh_sach = api.fetch_friends()
            label = "bạn bè"
            thread_type = ThreadType.USER
    except Exception as e:
        return await interaction.followup.send(f"❌ Không lấy được danh sách Zalo: {e}")

    if not danh_sach:
        return await interaction.followup.send(f"⚠️ Không có {label} nào.")

    # ✅ Hiển thị toàn bộ danh sách không giới hạn
    msg = f"**Danh sách {label}:**\n"
    for i, item in enumerate(danh_sach):
        msg += f"{i+1}. **{item['name']}** | ID: `{item['id']}`\n"
    msg += "\nNhập STT các mục muốn spam (phân cách dấu phẩy):"

    chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)

    try:
        reply = await bot.wait_for("message", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱ Hết thời gian chọn")

    try:
        picks = [int(x.strip()) - 1 for x in reply.content.strip().split(",")]
        ids = [danh_sach[i]['id'] for i in picks if 0 <= i < len(danh_sach)]
    except:
        return await interaction.followup.send("❌ STT không hợp lệ")

    if not ids:
        return await interaction.followup.send("❌ Không có mục nào được chọn")

    tool = SpamTool(
        name=f"ZALO#{interaction.user.id}",
        imei=imei,
        cookies=cookies_dict,
        thread_ids=ids,
        thread_type=thread_type,
        use_typing=False
    )

    stop_event = threading.Event()
    start_time = datetime.now()

    th = threading.Thread(target=lambda: tool.send_spam([message], delay), daemon=True)
    th.start()

    discord_user_id = str(interaction.user.id)
    with ZALO_LOCK:
        if discord_user_id not in user_zalo_tabs:
            user_zalo_tabs[discord_user_id] = []
        user_zalo_tabs[discord_user_id].append({
            "tool": tool,
            "thread": th,
            "stop_event": stop_event,
            "targets": ids,
            "type": label,
            "message": message,
            "delay": delay,
            "start": start_time
        })

    await interaction.followup.send(
        f"✅ Đã tạo tab spam Zalo cho <@{discord_user_id}>:\n"
        f"• Mục tiêu: `{', '.join(ids)}`\n"
        f"• Kiểu: `{label}`\n"
        f"• Nội dung: `{message}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
@tree.command(
    name="tabtreozalo",
    description="Quản lý/dừng tab treo Zalo"
)
async def tabtreozalo(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message(
            "Bạn không có quyền sử dụng lệnh này"
        )

    discord_user_id = str(interaction.user.id)
    with ZALO_LOCK:
        tabs = user_zalo_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message(
            "❌ Bạn không có tab treo Zalo nào đang hoạt động."
        )

    msg = "**📋 Danh sách tab treo Zalo của bạn:**\n"
    for idx, tab in enumerate(tabs, start=1):
        uptime = (datetime.now() - tab["start"]).total_seconds()
        hours, rem = divmod(int(uptime), 3600)
        minutes, seconds = divmod(rem, 60)
        msg += (
            f"{idx}. Kiểu: `{tab.get('type', '?')}` | "
            f"Mục tiêu: `{', '.join(map(str, tab.get('targets', [])))}` | "
            f"Delay: `{tab.get('delay', '?')}` giây | "
            f"Uptime: `{hours:02}:{minutes:02}:{seconds:02}`\n"
        )
    msg += "\n⏳ Nhập **số tab** để dừng tab tương ứng."

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱ Hết thời gian chọn. Không dừng tab nào.")

    try:
        index = int(reply.content.strip())
        if not (1 <= index <= len(tabs)):
            raise ValueError()
    except:
        return await interaction.followup.send("❌ Số tab không hợp lệ.")

    with ZALO_LOCK:
        chosen = tabs.pop(index - 1)
        chosen["tool"].running = False  # Dừng thread spam
        if not tabs:
            del user_zalo_tabs[discord_user_id]

    await interaction.followup.send(f"✅ Đã dừng tab treo Zalo số `{index}`")
    

async def notify_user_token_die(user_id: str, token: str, status_code: int):
    user = await bot.fetch_user(int(user_id))
    if user:
        try:
            await user.send(
                f"\u26a0\ufe0f Token `{token[:20]}...` \u0111\u00e3 b\u1ecb **DIE** v\u1edbi m\u00e3 l\u1ed7i `{status_code}` v\u00e0 \u0111\u00e3 \u0111\u01b0\u1ee3c x\u00f3a kh\u1ecfi tab c\u1ee7a b\u1ea1n."
            )
        except Exception as e:
            print(f"[!] Kh\u00f4ng th\u1ec3 g\u1eedi tin nh\u1eafn DM t\u1edbi user {user_id}: {e}")

async def remove_dead_token(user_id: str, token: str):
    async with DIS_LOCK:
        if user_id in user_discord_tabs:
            for tab in user_discord_tabs[user_id]:
                if token in tab["tokens"]:
                    index = tab["tokens"].index(token)
                    tab["tokens"].pop(index)
                    tab["delays"].pop(index)
                    print(f"[\u2713] \u0110\u00e3 x\u00f3a token DIE: {token[:15]}...")

async def _discord_spam_worker(session, token, channels, message, delay, start_time, user_id):
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJjbGllbnRfdmVyc2lvbiI6IjEwMC4wLjAuMCJ9"
    }
    while True:
        for channel_id in channels:
            content = message[:2000] if len(message) > 2000 else message
            data = {"content": content}
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            try:
                async with session.post(url, headers=headers, json=data) as resp:
                    status = resp.status
                    if status in [200, 201]:
                        print(f"[\u2713] {token[:15]}... | G\u1eedi ID {channel_id}")
                    elif status in [401, 403]:
                        print(f"[\u00d7] Token DIE {token[:15]}... | Status: {status}")
                        await notify_user_token_die(user_id, token, status)
                        await remove_dead_token(user_id, token)
                        return
                    else:
                        err = await resp.text()
                        print(f"[\u00d7] Token {token[:15]}... | L\u1ed7i {channel_id} | {status} | {err}")
            except Exception as e:
                print(f"[!] Ngo\u1ea1i l\u1ec7 token {token[:15]}...: {e}")
            await asyncio.sleep(delay)

@tree.command(name="nhaymess", description="Spam nhây Facebook bằng cookie")
@app_commands.describe(
    cookies="Cookie (cách nhau dấu phẩy)",
    box_ids="ID Box (cách nhau dấu phẩy)",
    ten_reo="Tên cần réo (tuỳ chọn)",
    delay="Delay mỗi tin (giây)"
)
async def nhaymess(interaction: discord.Interaction, cookies: str, box_ids: str, ten_reo: str = "", delay: float = 2.0):
    await interaction.response.defer()
    discord_user_id = str(interaction.user.id)

    cookie_list = [x.strip() for x in cookies.split(",") if x.strip()]
    id_list = [x.strip() for x in box_ids.split(",") if x.strip()]
    messengers = []

    for c in cookie_list:
        try:
            messengers.append(Kem(c))
        except Exception as e:
            print(f"[!] Cookie lỗi: {e}")

    if not messengers:
        return await interaction.followup.send("❌ Tất cả cookie đều lỗi!")

    chon_name = ten_reo or ""
    CAU_CHUI = [
f"ccho sua lofi de {chon_name}",
f"sua di {chon_name} em😏🤞",
f"lofi di {chon_name} cu😝",
f"tk ngu lon {chon_name} eyy🤣🤣",
f"nhanh ti em {chon_name}🤪👌",
f"cam a {chon_name} mo coi😏🤞",
f"hang hai len ti {chon_name} de👉🤣",
f"cn tat nguyen {chon_name}😏??",
f"cn 2 lai mat mam {chon_name}🤪👎",
f"anh cho may sua a {chon_name}😏🤞",
f"ah ba meta 2025 ma {chon_name}😋👎",
f"bi anh da na tho cmnr dk {chon_name}🤣",
f"thieu oxi a {chon_name}🤣🤣",
f"anh cko may oxi hoa ne {chon_name}😏👉🤣",
f"may cay cha qua a cn ngu {chon_name}🤪",
f"may phe nhu con me may bi tao hiep ma {chon_name}🤣",
f"dung ngam dang nuot cay tao nha coan {chon_name}👉🤣",
f"con cho {chon_name} cay tao ro👉🌶",
f"oc cho ngoi do nhay voi tao a {chon_name}🤣",
f"me may bi tao cho len dinh r {chon_name}=))",
f"ui cn ngu {chon_name} oc cac=))",
f"cn gai me may khog bt day nay a {chon_name} cn oc cac😝",
f"cn cho {chon_name} may cam a:))?",
f"cam lang that r a cn ngu {chon_name}🤣",
f"ui tk cac dam cha chem chu ak {chon_name}😝🤞",
f"cn cho dot so tao run cam cap me roi ha em {chon_name} =))",
f"ui cai con hoi {chon_name}👉🤣",
f"cn me may chet duoi ao roi kia {chon_name}😆",
f"djt con {chon_name} cu cn lon tham:))",
f"ui con bem {chon_name} nha la nhin phen v:))",
f"con cho cay gan nha sua di {chon_name}😏",
f"con bem {chon_name} co me khog😏🤞",
f"a quen may mo coi tu nho ma {chon_name}🤣",
f"sua chill de {chon_name} oc🤣",
f"hay cam nhan noi dau di em {chon_name}:))))",
f"hinh anh con bem {chon_name} gie rach bi anh cha dap:))))))",
f"ti anh chup dang tbg la may hot nha {chon_name}🤣",
f"a may muon hot cx dau co de cn ngu {chon_name}👉🤣🤣",
f"oi may bi cha suc pham kia {chon_name}-))",
f"tao co noti con boai {chon_name} so tao:)) ti tao cap dang profile 1m theo doi:))",
f" {chon_name} con o moi khong bame bi tao khinh thuong=)))",
f"may con gi khac hon khong con bem du ngu {chon_name}🤣",
f"cam canh cdy ngu bi cha chui khong giam phan khang a {chon_name}:))",
f"bi tao chui ma toi so a {chon_name}🤞",
f"nhin ga {chon_name} muon ia chay🤣",
f"con culi lua thay phan ban bi phan boi a {chon_name}:))",
f"may bi tao chui cho om han dk {chon_name}👉🤣🤣🤞",
f"bi tao chui cho so queo cac dung khong {chon_name}:))))",
f"dung cam han tao nua {chon_name}:))",
f"con dog {chon_name} bi tao chui ghi thu a:))",
f"su dung ngon sat thuong xiu de bem anh di mo {chon_name}=)))",
f"co sat thuong chi mang ko ay {chon_name}😝",
f"con ngheo nha la {chon_name} bi bo si va👉🤣🤣",
f"nao may co biet thu nhu anh vay {chon_name}🤪👌",
f"thang nghich tu {chon_name} sao may giet cha may the:))",
f"khong ngo thang phan nghich {chon_name} lua cha doi me=))",
f"tk ngu {chon_name} bi anh co lap ma-))",
f"phan khang di con cali {chon_name} mat map:))",
f"may con gi khac ngoai sua khong ay {chon_name}👉😏🤞",
f" {chon_name} mo coi=))",
f"bi cha chui phat nao ghi han phat do {chon_name} dk em:))",
f"may toi day de chi bi tao chui thoi ha {chon_name}:))",
f"bo la ac quy fefe ne {chon_name}🤣🤣",
f"nen bo lay cay ak ban nat so may luon😏🤞",
f"keo lu ban an hai may ra lmj dc anh khong vay {chon_name}🤣🤞",
f"ui ui dung thang an hai mang ten {chon_name}:))",
f"dung la con can ba mxh chi biet nhin anh chui cha mang me no ma {chon_name}=))",
f"may co phan khang duoc khong vay:)) {chon_name}",
f"may khong phan khang duoc a {chon_name}=))",
f"may yeu kem den vay a con cali {chon_name}😋👎",
f"con cali {chon_name} mat mam cay ah roi🌶",
f"cu anh lam dk em {chon_name}:))",
f"may co biet gi ngoai sua kiki dau ma {chon_name}👉🤣🤣",
f"may la chi qua qua ban may la chi gau gau ha {chon_name}=))",
f"mua skill di em {chon_name}🤪🤞",
f"anh mua skill duoc ma em {chon_name}😏🤞",
f"anh mua skill vo cai lon me may ay em {chon_name}:))",
f"con culi {chon_name} said : sap win duoc anh roi mung vai a🤣",
f"con cali {chon_name} nghi vay nen mung lam dk:)) {chon_name}",
f"win duoc anh dau de dau em {chon_name}🤪🤞",
f"con cho dien {chon_name} sua dien cuong nao🤣",
f"ui ui con kiki {chon_name} cay anh da man a🌶",
f"tk mo coi {chon_name} sua belike a🤣",
f"chill ti di em {chon_name}🤣🤣",
f"sao sua ko chill gi het vay {chon_name}🤣🤣",
f"bi anh chui cho tat ngon a {chon_name}=))",
f"may sua mau khong anh dap may tat sua bh {chon_name}:))",
f"sua toi khi kiet que nha cn thu {chon_name}🤣🤣",
f"cam may ngung nha cn kiki {chon_name}😝",
f"bo mat nghen ngon a ma nhai hoai v {chon_name}:🤪👌",
f"tao cam 1887 ban ca gia pha nha may chet {chon_name} ay:))",
f"may thay anh ba qua nen sui cmnr a {chon_name}😜",
f"sao may cam vay {chon_name}🤪🤞",
f"may cam = tao win do {chon_name}🤣🤣",
f"may nham win duoc tao khong {chon_name}🤣",
f"ga ma hay sua vay {chon_name}👉🤣",
f"tao dem 123 may chua len tao giet con gia may do {chon_name}🤣",
f"ra tinh hieu de tao treo co con ba may die di {chon_name}:))",
f"may ra tinh hieu sos chay thoat than trc a {chon_name}🤣",
f"dung thang con bat hieu {chon_name}👉🤣🤣",
f"con me may moi de ra thang con bat hieu nhu vay🤣🤞",
f"thang con troi danh di bao gia pha a {chon_name}🤪🤞",
f"bao nhu may gap anh cung tat dien {chon_name}🤣🤞🤞",
f" {chon_name} bi anh chui off mxh la vua roi=))",
f"may lam lai anh khong vayy {chon_name}:))",
f"tao biet la khongg ma {chon_name}👉🤣",
f"do may bai tao all san ro cmnr ma {chon_name}🤣",
f"tao dep trai ma {chon_name}👉🤣",
f"nen may le luoi liem chan tao di {chon_name}🤪🤞",
f"o o ccho {chon_name} loe toe bo may dap vo mom🤣",
f"tk cac {chon_name} oc cho vai cuc👉🤣",
f"tk ngu {chon_name} thay hw la lam than a🤪🤞",
f"du ngu cung onl mxh a {chon_name}😏😏",
f"svat {chon_name} cay cu anh den tim tai het roi a🤣",
f"moi ti xiu ma go duoi roi a {chon_name}🤣",
f"anh speed ne tk ngu {chon_name}👉😏",
f"cn cho ngu {chon_name} moi 5p ma da met a🤣🤣",
f"tk bach tang {chon_name}",
f"ccho dot la {chon_name}",
f"ngu cn ra de a {chon_name}",
f"tk ngon lu {chon_name}",
f"sped di tk ga {chon_name}",
f"ga v em {chon_name}",
f"anh uoc ga giong may a {chon_name}",
f"o o cn nghich tu {chon_name}",
f"chay dau vay tk {chon_name} ngu",
f"anh cho may chay a {chon_name}",
f"chay nhanh vay em {chon_name}",
f"ma sao em thoat khoi anh duoc ha {chon_name} em",
f"co gang win anh di {chon_name}",
f"sap win dc roi do {chon_name}",
f"e e care t di ma {chon_name}",
f"sao ko giam {chon_name}",
f"roi roi cam lang a {chon_name}",
f"on khong vay {chon_name}",
f"bat on a {chon_name}",
f"bi tao chui ma sao on dc {chon_name}",
f"cn cali {chon_name} sua bay",
f"ai cho m sua v {chon_name}",
f"xin phep ah chua o {chon_name}",
f"da may chetme may ma cn culi {chon_name} du xe",
f"sao may bel vay em {chon_name}",
f"120kg a {chon_name}",
f"sao may khon v {chon_name}",
f"khon nhu con kiki nha tao🤣 {chon_name}",
f"sat thuog ti di em {chon_name}",
f"em kem coi v {chon_name}",
f"co gi khac khong {chon_name}",
f"khong co j a {chon_name}",
f"em phe vay la cung dk {chon_name}",
f"dung a🤣 {chon_name}",
f"roi roi {chon_name}",
f"cn phe {chon_name}",
f"leg keg di troi {chon_name}",
f"lien tuc {chon_name} di boa",
f"sao ko lien tuc {chon_name}",
f"yeu sinh ly a🤣 {chon_name}",
f"nang khong em {chon_name}",
f"so anh nen dai ra mau luon a {chon_name}",
f"cn culi {chon_name} mat mam",
f"gap gap len tk ngu {chon_name}",
f"anh speed vcl ma {chon_name}",
f"may slow vaicalonn {chon_name}",
f"an c j phe lam vay tk phe vat {chon_name}",
f"cay cu anh lam ma {chon_name}",
f"cay ma choi a {chon_name}",
f"nhin mat ns nhu trai ot kia {chon_name}",
f"choi la doi a {chon_name}",
f"sao hay v cn dog ten {chon_name}",
f"t cam ba chia dam dit bme may ma {chon_name}",
f"o o thg cn bat hieu nay chs gay vs cau {chon_name} a",
f"{chon_name} teu v em",
f"tau hai a {chon_name}",
f"cn an hai danh trong lang a {chon_name}",
f"duoi a {chon_name}",
f"nhin biet duoi r🤣 {chon_name}",
f"anh cho may rot a {chon_name}",
f"sao cam lang r {chon_name}",
f"roi roi cn ngu cam {chon_name}",
f"ccho {chon_name} nay phen ia v",
f"anh go ba vcl ay {chon_name}",
f"cay a {chon_name}",
f"Ngầu Êyy {chon_name}",
f"Cố lên con thú {chon_name}",
f"Tao cho mày ngậm chx ? {chon_name}",
f"Mày cút rồi hả {chon_name} ",
f"cố tí nữa {chon_name}",
f"speed nào {chon_name}",
f"nhây tới năm sau dc ko {chon_name}",
f"mạnh mẽ nào {chon_name}",
f"Con culi mocoi ey {chon_name}",
f"k đc à {chon_name}",
f"con chó ngu cố đê {chon_name}",
f"sao m câm kìa {chon_name}",
f"gà j {chon_name}",
f"mày sợ tao à =)) {chon_name}",
f"m gà mà {chon_name}",
f"mày ngu rõ mà {chon_name}",
f"đúng mà {chon_name}",
f"cãi à {chon_name}",
f"mày còn gì khác k {chon_name}",
f"học lỏm kìa {chon_name}",
f"cố tí em {chon_name}",
f"mếu à {chon_name}",
f"sao mếu kìa {chon_name}",
f"tao đã cho m mếu đâu {chon_name}",
f"va lẹ đi con dốt {chon_name}",
f"sao kìa {chon_name}",
f"từ bỏ r à {chon_name}",
f"mạnh mẽ tí đi con đĩ {chon_name}",
f"cố lên con chó ngu {chon_name}",
f"=)) cay tao à con đĩ {chon_name}",
f"sợ tao à {chon_name}",
f"sao sợ tao kìa {chon_name}"
f"cay lắm phải kh {chon_name}",
f"ớt rồi kìa em {chon_name}",
f"mày còn chối à {chon_name}",
f"làm tí đê {chon_name}",
f"mới đó đã mệt r kìa {chon_name}",
f"sao gà mà sồn v {chon_name}",
f"sồn như lúc đầu cho tao {chon_name}",
f"sao à {chon_name}",
f"ai cho m nhai {chon_name}",
f"cay lắm r {chon_name}", 
f"từ bỏ đi em {chon_name}",
f"mày nghĩ mày làm t cay đc à {chon_name}",
f"có đâu {chon_name}",
f"tao đang hành m mà {chon_name}",
f"bịa à {chon_name}",
f"cay :))))) {chon_name}",
f"cố lên chó dốt {chon_name}",
f"hăng tiếp đi {chon_name}",
f"tới sáng k em {chon_name}",
f"k tới sáng à {chon_name}",
f"chán v {chon_name}",
f"m gà mà {chon_name}",
f"log acc thay phiên à {chon_name}",
f"coi tụi nó dồn ngu kìa {chon_name}",
f"sợ tao à con chó đần {chon_name}",
f"lại win à {chon_name}",
f"lại win r {chon_name}",
f"lũ cặc cay tao lắm🤣🤣 {chon_name}",
f"cố lên đê {chon_name}",
f"sao mới 5p đã câm r {chon_name}",
f"yếu đến thế à {chon_name}",
f"sao kìa {chon_name}",
f"khóc kìa {chon_name}",
f"cầu cứu lẹ ei {chon_name}",
f"ai cứu đc m à :)) {chon_name}",
f"tao bá mà {chon_name}",
f"sao m gà thế {chon_name}",
f"hăng lẹ cho tao {chon_name}",
f"con chó eiii🤣 {chon_name}",
f"ổn k em {chon_name}",
f"kh ổn r à {chon_name}",
f"mày óc à con chó bẻm=)) {chon_name}",
f"mẹ mày ngu à {chon_name}",
f"bú cặc cha m k em {chon_name}",
f"thg giả gái :)) {chon_name}",
f"coi nó ngu kìa ae {chon_name}",
f"con chó này giả ngu à {chon_name}",
f"m ổn k {chon_name}",
f"mồ côi kìa {chon_name}",
f"sao v sợ r à {chon_name}",
f"cố gắng tí em {chon_name}",
f"cay cú lắm r {chon_name}",
f"đấy đấy bắt đầu {chon_name}",
f"chảy nước đái bò r à em {chon_name}",
f"sao kìa đừng run {chon_name}",
f"mày run à:)) {chon_name}",
f"thg dái lở {chon_name}",
f"cay mẹ m lắm {chon_name}",
f"lgbt xuất trận à con đĩ {chon_name}",
f"thg cặc giết cha mắng mẹ {chon_name}",
f"sủa mạnh eii {chon_name}",
f"mày chết r à:)) {chon_name}",
f"sao chết kìa {chon_name}",
f"bị t hành nên muốn chết à {chon_name}",
f"con lồn ngu=)) {chon_name}",
f"sao kìa {chon_name}",
f"mạnh lên kìa {chon_name}",
f"yếu sinh lý à {chon_name}",
f"sủa đê {chon_name}",
f"cay à {chon_name}",
f"hăng đê {chon_name}",
f"gà kìa ae {chon_name}",
f"akakaa {chon_name}",
f"óc chó kìa {chon_name}",
f"🤣🤣🤣 {chon_name}",
f"ổn không🤣🤣 {chon_name}",
f"bất ổn à {chon_name}",
f"ơ kìaaa {chon_name}",
f"hăng hái đê {chon_name}",
f"chạy à 🤣🤣 {chon_name}",
f"tởn à {chon_name}",
f"kkkk {chon_name}",
f"mày dốt à {chon_name}",
f"cặc ngu {chon_name}",
f"cháy đê {chon_name}",
f"chat hăng lên {chon_name}",
f"cố lên {chon_name}",
f"mồ côi cay {chon_name}",
f"cay à {chon_name}",
f"cn chó ngu {chon_name}",
f"óc cac kìa {chon_name}",
f"đĩ đú:)) {chon_name}",
f"đú kìa {chon_name}",
f"cùn v {chon_name}",
f"r x {chon_name}",
f"hhhhh {chon_name}",
f"kkakak {chon_name}",
f"sao đú đó em {chon_name}",
f"cac teo a con {chon_name}",
f"ngu kìa {chon_name}",
f"chat mạnh đê {chon_name}",
f"hăng ee {chon_name}",
f"ơ ơ ơ {chon_name}",
f"sủa cháy đê {chon_name}",
f"sủa mạnh eei {chon_name}",
f"mày óc à con {chon_name}",
f"tao cho m chạy à {chon_name}",
f"con đĩ ngu sủa? {chon_name}",
f"mày chạy à con đĩ lồn {chon_name}",
f"co len con {chon_name}",
f"son hang len em {chon_name}",
f"sao m yeu v {chon_name} ",
f"co ti nua {chon_name}",
f"sao kia cham a {chon_name}",
f"hang hai len ti chu {chon_name}",
f"toi sang di {chon_name}",
f"co gang ti con cho {chon_name}",
f"yeu v con {chon_name}",
f"con cho {chon_name} co de",
f"sao m cam kia {chon_name}",
f"ga v {chon_name}",
f"may so a k dam chat hang ak {chon_name}",
f"m ga ma {chon_name}",
f"may ngu ro ma {chon_name}",
f"con {chon_name} an hai ma",
f"cai cun ak {chon_name}",
f"may con gi khac ko vay {chon_name}",
f"hoc dot nen nhay dot ak {chon_name}",
f"co ti di em {chon_name}",
f"meu a {chon_name}",
f"sao meu kia {chon_name}",
f"tao da cho m meu dau {chon_name}",
f"va le di con {chon_name} dot",
f"sao kia {chon_name}",
f"tu bo r a {chon_name}",
f"manh me ti di con {chon_name}",
f"co len con cho {chon_name} ngu",
f"😆 cay tao a con di {chon_name}",
f"so tao a {chon_name}",
f"sao cham roi kia {chon_name}",
f"cay lam phai kh {chon_name}",
f"{chon_name} ot anh cmnr",
f"may con choi a {chon_name}",
f"lam ti keo de {chon_name}",
f"moi do da met r ha {chon_name}",
f"sao ga ma son v {chon_name}",
f"son nhu luc dau cho tao di con {chon_name} dot",
f"sao duoi roi kia {chon_name}",
f"ai cho m nhai vay {chon_name}",
f"cay lam r a {chon_name}",
f"tu bo di em {chon_name}",
f"may nghi may lam t cay dc ha {chon_name}",
f"m dang cay ma {chon_name}",
f"tao dang hanh m ma {chon_name}",
f"keo nhay kg ay {chon_name}",
f"con mo coi {chon_name}",
f"co len {chon_name} oc cho",
f"hang tiep di {chon_name}",
f"toi sang k em {chon_name}",
f"met roi ha {chon_name}",
f"speed ti dc ko {chon_name}",
f"m ga ma {chon_name}",
f"thay phien a {chon_name}",
f"tui anh thay phien ban vo loz me con {chon_name} ma kaka",
f"so tao a con cho {chon_name}",
f"anh win me roi {chon_name} dot",
f"ga ma hay the hien ha {chon_name}",
f"con mo coi {chon_name} keo cai ko em",
f"co len de {chon_name}",
f"sao moi 1 ti ma da cam roi {chon_name}",
f"yeu vay ak {chon_name}",
f"sao kia {chon_name}",
f"bat luc r ak {chon_name}",
f"tim cach roi ha {chon_name}",
f"ai cuu dc m a :)) {chon_name}",
f"anh ba cmnr ma {chon_name}",
f"sao m ga vay {chon_name}",
f"hang le cho tao di {chon_name}",
f"con mo coi {chon_name}",
f"on k em {chon_name}",
f"bat on roi a {chon_name}",
f"may oc a con cho {chon_name}",
f"me may ngu a {chon_name}",
f"bu cac cha m k em {chon_name}",
f"mo coi {chon_name} cay anh ha",
f"me m dot tu roi a {chon_name}",
f"phe vay {chon_name}",
f"m on k {chon_name}",
f"mo coi kia {chon_name}",
f"sao v so r a {chon_name}",
f"co gang ti em {chon_name}",
f"cay cu lam r ha {chon_name}",
f"dien dai di em {chon_name}",
f"chay nuoc dai bo r a em {chon_name}",
f"sao kia dung so anh ma {chon_name}",
f"may run a:)) {chon_name}",
f"thg {chon_name} mo coi",
f"cay tao lam ha {chon_name}",
f"lgbt len phim ngu ak em {chon_name}",
f"thg cac giet cha mang me {chon_name}",
f"sua manh eii {chon_name}",
f"may chet r a:)) {chon_name}",
f"sao chet kia {chon_name}",
f"bi t hanh nen muon chet a {chon_name}",
f"con {chon_name} loz ngu kaka",
f"sao kia {chon_name}",
f"manh len kia {chon_name}",
f"yeu sinh ly a {chon_name}",
f"sua de {chon_name}",
f"cay a {chon_name}",
f"hang de {chon_name}",
f"con ga {chon_name}",
f"phe vat {chon_name}",
f"oc cho {chon_name}",
f"me m bi t du hap hoi kia con {chon_name}",
f"on ko em {chon_name}",
f"bat on ak {chon_name}",
f"o kiaaa sao vayy {chon_name}",
f"hang hai de {chon_name}",
f"chay ak {chon_name}",
f"so ak {chon_name}",
f"quiu luon roi ak {chon_name}",
f"may dot ak {chon_name}",
f"cac ngu {chon_name}",
f"chay de {chon_name}",
f"chat hang len {chon_name}",
f"co len {chon_name}",
f"{chon_name} mo coi",
f"cn cho ngu {chon_name}",
f"oc cac {chon_name}",
f"di du {chon_name}",
f"du kia {chon_name}",
f"cun v {chon_name}",
f"r luon con {chon_name} bi ngu roi",
f"met r am {chon_name}",
f"kkakak",
f"sao du {chon_name}",
f"cac con {chon_name}",
f"ngu kia {chon_name}",
f"chat manh de {chon_name}",
f"hang ee {chon_name}",
f"clm thk oc cho {chon_name}",
f"sua chay de {chon_name}",
f"sua manh eei {chon_name}",
f"may oc a con {chon_name}",
f"tao cho m chay a {chon_name}",
f"con mo coi {chon_name}",
f"may chay a con di lon {chon_name}",
f"sua de {chon_name}",
f"con phen {chon_name}",
f"bat on ho {chon_name}",
f"s do  {chon_name}",
f"sua lien tuc de {chon_name}",
f"moi tay ak {chon_name}",
f"choi t giet cha ma m ne {chon_name}",
f"hang xiu de {chon_name}",
f"th ngu {chon_name}",
f"len daica bieu ne {chon_name}",
f"sua chill de {chon_name}",
f"m thich du ko da {chon_name}",
f"son hang dc kg {chon_name}",
f"cam chay nhen {chon_name}",
f"m mau de {chon_name}",
f"duoi ak {chon_name}",
f"th ngu {chon_name}",
f"con {chon_name} len day anh sut chet me may",
f"m khoc ak {chon_name}",
f"sua lien tuc de {chon_name}",
f"thg {chon_name} cho dien",
f"bi ngu ak {chon_name}",
f"speed de {chon_name}",
f"cham v cn culi {chon_name}",
f"hoang loan ak {chon_name}",
f"bat on ak {chon_name}",
f"run ak {chon_name}",
f"chay ak {chon_name}",
f"duoi ak {chon_name}",
f"met r ak {chon_name}",
f"sua mau {chon_name}",
f"manh dan len {chon_name}",
f"nhanh t cho co hoi cuu ma m ne {chon_name}",
f"cam mach me nha {chon_name}",
f"ao war ak {chon_name}",
f"tk {chon_name} dot v ak",
f"cham chap ak {chon_name}",
f"th cho bua m sao v {chon_name}",
f"th dau buoi mat cho {chon_name}",
f"cam hoang loan ma {chon_name}",
f"lo lo sao may cam v {chon_name}",
f"ai cho may cam vayy {chon_name}",
f"anh cho chx ay=)) {chon_name}",
f"cmm hai a {chon_name}",
f"hai vay em {chon_name}",
f"co gi khac khong {chon_name}",
f"khong a {chon_name}",
f"ga den vay a {chon_name}",
f"thang an hai lien tuc di {chon_name}",
f"bi anh dap dau ma {chon_name}",
f"cay cu anh lam dk {chon_name}",
f"âkkak sua di em {chon_name}",
f"ccho ngu sua {chon_name}",
f"xem ns occho kia {chon_name}",
f"ngu hay sua a👉😏 {chon_name}",
f"alo alo cdy ngu {chon_name}👉🤪",
f"leg keg loc troc lay sa beg dap dau may {chon_name}👉🤣",
f"sua hang hai ti di em ey {chon_name}👉🤪",
f"may vua sua bi tao lay sa beg dap vo 2 hon trug dai ma {chon_name}👉😋",
f"o o cn culi {chon_name} bia ngu a👉🤣🤣",
f"cay anh ma lmj dc anh dau {chon_name} dk🤞🤞",
f"culi {chon_name} cn oc bem a con😋",
f"sao do coan zai {chon_name} cn sua dc khong ay👉😏",
f"khong a {chon_name}🤣🤣",
f"anh biet anh ba ma {chon_name}",
f"ccho ngu hay sua a {chon_name}🤪🤪",
f"mat may nhu trai ot roi kia {chon_name}🤣🤣",
f"ngu ngu bi anh dap dau vo cot dien chetme may nha {chon_name}🤣🤣",
f"anh thog minh vcll ma {chon_name}🤪🤪",
f"may ngu nguc vcll ma em {chon_name}🤣🤣",
f"dk {chon_name} em😏🤞",
f"dung a {chon_name}🤣🤣",
f"may lam tao cuoi dc roi ds {chon_name}🤪🤞",
f"dien siet duoc roi do {chon_name} ngu ey🤣🤣",
f"anh chuc may dien ko ai coi nha {chon_name}👉🤣",
f"bi anh hanh ha den die dk {chon_name}😏🤞",
f"anh dap chetme may ma {chon_name} em🤣🤣",
f"sua lam vay {chon_name} kiki🤣🤣",
f"cn me nay hap hoi a {chon_name}👉😏🤞",
f"may bua nhan a {chon_name}🤣🤣",
f"run ray khi gap a ma {chon_name}🤪🤞",
f"anh len san la may khiep so dk {chon_name}🤣🤣",
f"do ah ba qua nen may so dk {chon_name}👉😏",
f"may van xin anh tha thu ma {chon_name}😝🙏",
f"tao cam ak47 na vo dau mat chetme may {chon_name}😝🙏",
f"may sua dien cuong di {chon_name}🤣🤣",
f"cmm ngu the em {chon_name}🤣🤞",
f"ai ngu = may nua dau {chon_name} em 👉🤣🤞",
f"may nhu culi giang tran vay {chon_name}🤣🤣",
f"may ma culi j may lgbt ma {chon_name} em🤣",
f"anh ba dao san war ma {chon_name} cu😝👎",
f"may an cut san treo ma {chon_name} 👉🤣🤞",
f"bu cut tao song qua ngay ma {chon_name}🤣🤣",
f"xao lon cn gay a {chon_name}😝",
f"culi biet sua la day a {chon_name}😏🤞",
f"ga ma gay quai vay {chon_name}🤪👌",
f"may can ngon roi a {chon_name}😏🤞",
f"con gi khac hon khong {chon_name}🤪🤪",
f"khog a {chon_name}🤣",
f"ngu den vay la cung ha {chon_name}😏🤞",
f"sao may phe nhan vay😏🤞",
f"con nghich tu phan loan {chon_name}🤣🤣",
f"con cho chiu so phan di {chon_name}😏🤞",
f"chiu so phan bi anh dam cha giet ma {chon_name} ha🤣🤣",
f"anh cs hoi dau may tu tra loi a {chon_name}🤣",
f"tk bua nhan {chon_name}😏🤞",
f"sao culi khong sua nx di {chon_name}🤣🤣",
f"nin ngon roi a {chon_name}🤣🤪",
f"gap phai cha la may phai ngam ot roi {chon_name}🤣🤣",
f"ngon xam cac lay len doi bem ah a tk culi {chon_name}🤪🤞",
f"cn cali mat mam sua j ay {chon_name}😏🤞",
f"len nhay vs ah toi trang tron di {chon_name}😝",
f"sao ay tai mat roi a {chon_name}🤣🤣",
f"so lam roi a {chon_name}😏🤞",
f"co may anh da dau may toi chet me {chon_name}🤣",
f"dcm cay cu anh a {chon_name}🤣🤣",
]

    class NhayReoWorker:
        def __init__(self, messengers, box_ids, messages, delay, stop_event):
            self.messengers = messengers
            self.box_ids = box_ids
            self.messages = messages
            self.delay = delay
            self.stop_event = stop_event

        def run(self):
            idx = 0
            while not self.stop_event.is_set():
                for messenger in self.messengers:
                    for box_id in self.box_ids:
                        msg = self.messages[idx % len(self.messages)]
                        result = messenger.gui_tn(box_id, msg)
                        if result.get("success"):
                            print(f"[NHAY][{messenger.user_id}] → {box_id}: OK")
                        else:
                            print(f"[NHAY][{messenger.user_id}] → {box_id}: FAIL")
                        time.sleep(0.2)
                idx += 1
                time.sleep(self.delay)

    stop_event = threading.Event()
    start_time = datetime.now()

    worker = NhayReoWorker(messengers, id_list, CAU_CHUI, delay, stop_event)
    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()

    if discord_user_id not in user_nhaymess_tabs:
        user_nhaymess_tabs[discord_user_id] = []
    user_nhaymess_tabs[discord_user_id].append({
        "messengers": messengers,
        "box_ids": id_list,
        "delay": delay,
        "start_time": start_time,
        "stop_event": stop_event,
        "thread": thread
    })

    embed = discord.Embed(title="✅ Đã tạo tab nhây mess", color=0x00ff00)
    embed.add_field(name="👤 Người dùng", value=f"<@{discord_user_id}>", inline=False)
    embed.add_field(name="📨 To", value=", ".join(id_list), inline=False)
    embed.add_field(name="📡 Tài khoản", value=str(len(messengers)), inline=True)
    embed.add_field(name="⏱ Delay", value=f"{delay} giây", inline=True)
    embed.add_field(name="🕰 Bắt đầu", value=start_time.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

    await interaction.followup.send(embed=embed)            
                                    


@tree.command(name="tabnhaymess", description="Xem tab đang chạy và dừng từng tab")
async def tabnhaymess(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)
    tabs = user_nhaymess_tabs.get(discord_user_id, [])
    if not tabs:
        return await interaction.response.send_message("⚠️ Không có tab nào đang chạy.")

    desc = ""
    for idx, tab in enumerate(tabs):
        elapsed = (datetime.now() - tab["start_time"]).total_seconds()
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        uptime = f"{h:02}:{m:02}:{s:02}"
        desc += (
            f"**{idx + 1}.** Box: `{', '.join(tab['box_ids'])}` | "
            f"Delay: `{tab['delay']}s` | Uptime: `{uptime}`\n"
        )

    embed = discord.Embed(title="📋 Danh sách tab nhây đang chạy", description=desc, color=0x3498db)
    embed.set_footer(text="Trả lời tin nhắn này bằng STT để dừng tab.")
    await interaction.response.send_message(embed=embed)

    def check(msg):
        return (
            msg.author.id == interaction.user.id and 
            msg.channel.id == interaction.channel.id and 
            msg.content.isdigit()
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        stt = int(msg.content.strip()) - 1
        if 0 <= stt < len(tabs):
            tabs[stt]["stop_event"].set()
            del tabs[stt]
            if not tabs:
                del user_nhaymess_tabs[discord_user_id]
            await msg.reply("🛑 Đã dừng tab thành công.")
        else:
            await msg.reply("❌ STT không hợp lệ.")
    except:
        await interaction.followup.send("⏰ Hết thời gian chọn STT.")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot {bot.user} đã dậy theo lệnh của chủ nhân Mạnh Bùi")

import asyncio
import time
from datetime import datetime
import aiohttp
import discord

# ====== BIẾN TOÀN CỤC ======
DIS_LOCK = asyncio.Lock()       # lock cho treo tin nhắn
DIS_IMG_LOCK = asyncio.Lock()   # lock cho treo ảnh

user_discord_tabs = {}      # lưu task treo tin nhắn
user_discord_img_tabs = {}  # lưu task treo ảnh


# ====== HÀM CHECK QUYỀN ======
def has_permission(interaction: discord.Interaction) -> bool:
    return True  # bạn tự sửa lại theo logic quyền


# ====== WORKER SPAM TIN NHẮN ======
async def _discord_spam_worker(session, token, channels, message, delay, start_time, uid):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    while True:
        for channel_id in channels:
            try:
                url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                payload = {"content": message}
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200 and resp.status != 201:
                        print(f"[{uid}] Error send msg {channel_id}: {resp.status}")
            except Exception as e:
                print(f"[{uid}] Exception send msg: {e}")
        await asyncio.sleep(delay)


# ====== WORKER SPAM ẢNH ======
async def _discord_spam_worker_img(session, token, channels, image_url, delay, start_time, uid):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    while True:
        for channel_id in channels:
            try:
                url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                payload = {"content": image_url}
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200 and resp.status != 201:
                        print(f"[{uid}] Error send img {channel_id}: {resp.status}")
            except Exception as e:
                print(f"[{uid}] Exception send img: {e}")
        await asyncio.sleep(delay)


# ====== FORMAT TIME ======
def format_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ====== MODAL TREO TIN NHẮN ======
class TreoDisModal(discord.ui.Modal, title="🌀 Treo Discord - Tin nhắn"):
    token = discord.ui.TextInput(label="⚡Token", required=True)
    channel_id = discord.ui.TextInput(label="⚡Channel ID", required=True)
    message = discord.ui.TextInput(label="⚡Nội dung", style=discord.TextStyle.paragraph, required=True)
    delay = discord.ui.TextInput(label="⚡Delay (s)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        token = self.token.value.strip()
        channel_id = self.channel_id.value.strip()
        message = self.message.value.strip()
        try:
            delay = float(self.delay.value.strip())
        except:
            embed = discord.Embed(title="⚠️ Lỗi nhập delay", description="Delay phải là số!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not has_permission(interaction):
            embed = discord.Embed(title="🚫 Không có quyền", description="Bạn không có quyền sử dụng bot.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        session = aiohttp.ClientSession()
        start_time = datetime.now()
        uid = str(interaction.user.id)
        tasks = [asyncio.create_task(_discord_spam_worker(session, token, [channel_id], message, delay, start_time, uid))]

        async with DIS_LOCK:
            if uid not in user_discord_tabs:
                user_discord_tabs[uid] = []
            user_discord_tabs[uid].append({
                "session": session, "tasks": tasks,
                "channels": [channel_id], "tokens": [token],
                "delays": [delay], "message": message,
                "start": start_time, "type": "Tin nhắn"
            })

        embed = discord.Embed(
            title="✅ Đã tạo tab treo Discord (Tin nhắn)",
            description=f"👤 Người dùng: <@{uid}>\n• Channel: `{channel_id}`\n• Delay: `{delay}`s\n• Bắt đầu: `{start_time.strftime('%H:%M:%S')}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


# ====== MODAL TREO ẢNH ======
class TreoAnhDisModal(discord.ui.Modal, title="🌀 Treo Discord - Ảnh"):
    token = discord.ui.TextInput(label="⚡Token", required=True)
    channel_id = discord.ui.TextInput(label="⚡Channel ID", required=True)
    image_url = discord.ui.TextInput(label="⚡Link ảnh", placeholder="VD: https://files.catbox.moe/xxx.png", required=True)
    delay = discord.ui.TextInput(label="⚡Delay (s)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        token = self.token.value.strip()
        channel_id = self.channel_id.value.strip()
        image_url = self.image_url.value.strip()
        try:
            delay = float(self.delay.value.strip())
        except:
            embed = discord.Embed(title="⚠️ Lỗi nhập delay", description="Delay phải là số!", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not has_permission(interaction):
            embed = discord.Embed(title="🚫 Không có quyền", description="Bạn không có quyền sử dụng bot.", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        session = aiohttp.ClientSession()
        start_time = datetime.now()
        uid = str(interaction.user.id)
        tasks = [asyncio.create_task(_discord_spam_worker_img(session, token, [channel_id], image_url, delay, start_time, uid))]

        async with DIS_IMG_LOCK:
            if uid not in user_discord_img_tabs:
                user_discord_img_tabs[uid] = []
            user_discord_img_tabs[uid].append({
                "session": session, "tasks": tasks,
                "channels": [channel_id], "tokens": [token],
                "delays": [delay], "image": image_url,
                "start": start_time, "type": "Ảnh"
            })

        embed = discord.Embed(
            title="✅ Đã tạo tab treo Discord (Ảnh)",
            description=f"👤 Người dùng: <@{uid}>\n• Channel: `{channel_id}`\n• Delay: `{delay}`s\n• Ảnh: [Link]({image_url})\n• Bắt đầu: `{start_time.strftime('%H:%M:%S')}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


# ====== VIEW (NÚT CHỌN) ======
class AllTreoDisView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Treo tin nhắn", style=discord.ButtonStyle.green)
    async def treo_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TreoDisModal())

    @discord.ui.button(label="🖼️ Treo ảnh", style=discord.ButtonStyle.blurple)
    async def treo_img(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TreoAnhDisModal())



@tree.command(name="alltreodis", description="Treo tin nhắn hoặc ảnh lên Discord")
async def alltreodis(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(title="🚫 Không có quyền", description="Bạn không có quyền sử dụng bot.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    embed = discord.Embed(
        title="🌀 Tool Treo Discord",
        description="Chọn một phương thức để tiếp tục:",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=AllTreoDisView())



@tree.command(name="taballtreodis", description="Quản lý/dừng tất cả tab treo Discord (tin nhắn & ảnh)")
async def taballtreodis(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description="Bạn không có quyền sử dụng bot.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    discord_user_id = str(interaction.user.id)


    async with DIS_LOCK:
        text_tabs = list(user_discord_tabs.get(discord_user_id, []))
    async with DIS_IMG_LOCK:
        img_tabs = list(user_discord_img_tabs.get(discord_user_id, []))

    all_tabs = text_tabs + img_tabs

    if not all_tabs:
        embed = discord.Embed(
            title="❌ Không có tab treo",
            description="Bạn chưa có tab treo nào đang hoạt động.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)


    embed = discord.Embed(
        title="📋 Danh sách tab treo Discord",
        description="➡️ Nhập số thứ tự của tab bạn muốn dừng (30s).",
        color=discord.Color.blurple()
    )

    for idx, tab in enumerate(all_tabs, 1):
        channels = ",".join(map(str, tab.get("channels", []))) or "—"
        delays = ",".join(map(str, tab.get("delays", []))) or "—"
        method = tab.get("type", "Không rõ")

        started = tab.get("start")
        uptime = "—"
        if started:
            try:
                if hasattr(started, "timestamp"):
                    elapsed = int((datetime.now() - started).total_seconds())
                else:
                    elapsed = int(time.time() - float(started))
                uptime = format_time(elapsed)
            except Exception:
                pass

        embed.add_field(
            name=f"#{idx} | {method}",
            value=(f"📡 Kênh: `{channels}`\n"
                   f"🕒 Delay: `{delays}` giây\n"
                   f"⏳ Uptime: {uptime}"),
            inline=False
        )

    await interaction.response.send_message(embed=embed)


    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏱️ Hết thời gian",
            description="Không dừng tab nào.",
            color=discord.Color.orange()
        )
        return await interaction.followup.send(embed=embed)

    c = reply.content.strip()
    if not c.isdigit() or not (1 <= int(c) <= len(all_tabs)):
        embed = discord.Embed(
            title="⚠️ Không hợp lệ",
            description="Bạn phải nhập số thứ tự hợp lệ.",
            color=discord.Color.yellow()
        )
        return await interaction.followup.send(embed=embed)

    i = int(c)
    tab = all_tabs[i - 1]


    for t in tab.get("tasks", []):
        try:
            t.cancel()
        except:
            pass
    session = tab.get("session")
    if session:
        try:
            await session.close()
        except:
            pass

    async with DIS_LOCK:
        if discord_user_id in user_discord_tabs and tab in user_discord_tabs[discord_user_id]:
            user_discord_tabs[discord_user_id].remove(tab)
            if not user_discord_tabs[discord_user_id]:
                user_discord_tabs.pop(discord_user_id, None)
    async with DIS_IMG_LOCK:
        if discord_user_id in user_discord_img_tabs and tab in user_discord_img_tabs[discord_user_id]:
            user_discord_img_tabs[discord_user_id].remove(tab)
            if not user_discord_img_tabs[discord_user_id]:
                user_discord_img_tabs.pop(discord_user_id, None)

    embed = discord.Embed(
        title="⛔ Tab đã dừng",
        description=f"Bạn đã dừng thành công tab số `{i}` (phương thức: {tab.get('type','?')}).",
        color=discord.Color.red()
    )
    return await interaction.followup.send(embed=embed)





import asyncio
import aiohttp
import sys
import gc
from datetime import datetime
import itertools

# ================== NHAYDIS NAM / NỮ ==================

# Bộ tin nhắn cho từng đối tượng
MESSAGES_NAM = [
    "# sủa gì sủa lại bố nghe nào con chó rách =))",
" # mồ côi thắp hương cha mẹ trc khi chửi chưa",
" # m có cảnh kh thk óc cặc",
" # đánh con mẹ m luôn đê",
" # rén lắp bắp không nên lời à",
" # mồ côi mới ra khỏi trại trẻ mồ côi mà ngông à thk vô sinh=))",
" # đụ con gái mẹ mày tử vong nha thk lgbt óc chó =))",
" # t là hắc bạch vô thường t bắt con đĩ mẹ m vô đồn =))",
" # thk cặc lên 3 đòi đi war =))",
" # mồ côi không cha không mẹ sủa tiếng của con mẹ nó trước khi chết đã để lại cho nó =))=))",
" # tao chửi cho con đĩ mẹ mày cùng cả gia phả mày phải chui xuống đáy xã hội trốn mà =))",  
" # con chó tây tạng béo mỡ bị cha chọc nổ mỡ chết tươi rồi😹",
" # m còn trò j thể hiện nhanh lên ơ kìa",
" # giãy dụa trong tuyệt vọng à =))",
" # thk ngu cay cú khi bất lực nhìn người yêu nó bị t hành cho ra bã =))",
" # thk lồn trâu dái chó đéo có trình mà ngông =))",
" # cay muốn liệt tinh hoàn luôn à ",
" # nhai ngôn t là t cắt dái chó của cha m t đem chiên lên cho con đĩ mẹ m ăn đó",
" # óc chó ko trình lên đây xem con mẹ mày bị tao đụ tung lồn à😹",
" # cố gắng phản kháng hết sức bình sinh đi thằng óc chó phế vật hốc hại ơi =))=))=))",
" # câm lặng rồi à =))=))=))",
" # thk ngu chửi nhanh nhanh lên đi",
" # lề mề là con mẹ m tắc thở đó",
" # dừng 1 giây là cả nhà mày chôn thây =))",
" # chửi ngu là t đào mộ con mẹ mày lên t ỉa vô mồm bả đó =))",
" # thk ngu mặt thì bóng loáng như mấy con sinh vật da trơn , lỗ mũi thì thò lò ra cả nhúm lông , chân tay thì ghẻ lên ghẻ xuống , ghẻ luôn cả cái tâm hồn lẫn thể xác =))=))=))",
" # cái thứ óc cặc bị diêm vương tra tấn , con mẹ mày phải địt nhau với diêm vương để diêm vương tha tội cho thứ vô dụng hốc hại ăn mày như mày hả con đĩ điếm thúi tha ",
" # tao cầm que củi đụ vô cái lỗ đít dính cứt của con mẹ mày cho mẹ mày qua đời nha thk óc cặc mặt lồn súc vật ăn hại",
" # phế vật nằm la liệt 1 chỗ như người thực vật r à em =))",
" # cái thứ bất hiếu chó đẻ cặc tật khiếm khuyết tinh trùng óc lồn cặn bã mặt thì bẩn thỉu như cái lồn dính tinh của con đĩ mẹ mày vừa với đụ nhau với chó dái rồi nó bắn tinh vô họng con đĩ mẹ mày nè cái đĩ cha mày nha thằng phế vật =))=))",
" # con mẹ m tái sinh chỉ để được t đụ tiếp vì t đụ quá phê =))",
" # lêu lêu cái thằng ngu không làm gì được anh nên cay muốn đứt mạch máu não kìa",
" # cái con lồn nghiệt súc bú cặc chó để giải tỏa cơn thèm cặc =))=))=))",
" # kkk óc chó chửi nhau vs t bị t nhét bả chó vô họng nên giờ co giật sắp qua đời =))=))=))",
" # cay cú a đến mức phải thắp hương xin các ngài trên trời phù hộ để chửi win đc a =))=))=))",
" # biết gì chưa con chó đẻ =))=))",
" # tao là người đụ cái lồn mẹ mày từ trên thiên đàng dáng xuống 18 tầng địa ngục nè thằng cặc 🤪👌",
" # tao đẩy bay mày vào cối xay người trong địa ngục cho nó nghiến nát cái thứ súc sinh chó đẻ mày nha con đĩ 👊😋",
" # chém rách bao quy đầu của con cặc thằng cụ mày nha=))",
" # óc cặc cố gắng tỏ vẻ điềm tĩnh để ngầu ngầu nhưng dái nó run bần bật =))",
" # cố gắng bình tĩnh cái đéo mẹ nhà thằng mái lá xây bằng rơm =))",
" # tao cầu mưa cầu gió kéo sấm sét đánh vô cái đầu chó của mày nha cái thứ óc cặc ngu dốt 12 kiếp nạn 🥱",
" # tao cầm búa của tha nót tao rã thẳng vô cái lỗ lồn của con mẹ mày nè thằng óc chó 🥵🤙",
" # óc chó ngu nghèo cay cha bán mạng đi chửi cha má kìa=))",
" # bố cho m chạy chưa con đĩ =))=))=)",
" # t chưa cho m chạy mà con chó hoang mồ côi cha mẹ ơi",
" # ai đụng gì óc chó để nó sợ rồi chạy thục mạng tuột quần kìa",
" # óc lồn có trình chửi đâu",
" # thèm cặc chó thì nói đi em =)))=))",
" # ngu lồn bị chửi cho ngu người kìa",
" # con gái mẹ m giao phối với con chó hoang ngoài đầu đường phố đèn đỏ để đẻ ra mày mà em =))",
" # culi ngu bị anh chửi té tát xong h lại nghĩ ra kế chạy là thượng sách =))=))=))😹😹😹",
" # thằng nguuu giết cha bóp cổ má để cầu win anh à 😏 👉",
" # sủa tiếng mán con đĩ mẹ mày à em =))"
" # con mẹ mày bị tao cầm kiếm chọc thẳng từ hốc đít lên tận não bộ rồi tử vong mà thằng mồ côi ngu ơi 😁👎",
" # mày bị toàn thế giới xa lánh vì bede mà thằng cặc khắm 🥴🤟",
" # óc chó bị anh rã vô cặc cho cay muốn liệt tinh hoàn à 🫵😂",
" # anh có sức mạnh cho mày độn thổ cùng con má mày luôn mà 😂🤟",
" # tao là người chặt cặc thằng cha mày xong tao cắm cặc vô lỗ đít con bò nhà mày đó 🤣👌",
" # tao lái xe tải tông thẳng vô cái thân già của thằng cha mày mà thằng ngu 😁👎",
" # bố mày còn tống mày vô ngục tối 30 năm để vắt cạn tinh dịch mày cho con gái mẹ mày uống mà 🥴👌",
" # chị gái mày phải làm nô lệ tình dục cho tao để trả nợ cho cả nhà mày mà thằng ngu óc chó ơi 🥵👌",
" # con mẹ mày hằng ngày phải liếm cặc cho tao để thỏa mãn tao mà 🤣🤟",
" # hi vọng làm dân war của con ngu bị t dập tắt từ khi nó sủa điên trước mặt ae t=)))",
" # óc lồn thèm bú dái chó đực cay t à =))",  
" # bà nội m loạn luân vs bố m còn ông ngoại m loạn luân vs mẹ m mà thg não cún =)) 🤪",
" # Cn thú mại dâm bán dâm mà như bán trinh hoa hậu v🤣",
" # lồn cha con đĩ mẹ mày bị anh tông xe tử vong qua đời nên h cái con ngu lgbt này ôm hận anh suốt phần đời còn lại =))",
" # mẹ mày bị bọn tao hiếp dâm bắn tinh ngập tử cung nên qua đời vì 150l tinh trùng trong người đó =))",
" # con ngu nứng quá đến cả ông ngoại nó gần u80 r nó vẫn ko tha=))",
" # Mẹ mày làm con chó canh cửa cho nhà t mà🤣",  
" # đáp ngôn nhanh hơn tý đc k tk ngu xuẩn🌬 🤢🤢",
" # bắt quả tang con chó chạy bố nè",
" # não cún chỉ biết âm thầm seen và ôm gối khóc mà huhuh 👈😜",
" # con cave đú đởn kh có tiền đi học như bọn anh🤣🤣",
" # cả gia phả mày địt nhau trên bàn thờ ông công ông táo mà =))=))=))",
" # con đĩ mẹ mày bất lực vì bị t đụ cho lên bờ xuống ruộng =))=))=))",
" # mẹ mày bị t đụ đột quỵ ngoài nhà nghỉ kìa đem hòm ra nha",
" # đem hai cái mày với con mẹ m luôn nha",
" # à mà con chó này lmj đủ trình nằm hòm =)))=))=))",
" # nó pk nằm dưới bãi cứt anh ỉa mới đúng chứ =)))",
" # nhai t là t chặt đầu con đĩ má m ra đó",
" # thằng ngu lgbt da đen sủa lẹ ai cko mày câm",
" # thằng sex thú đang cố làm cha cay hả thằng bại não",
" # tao bất tử với sát thw của cái ngôn con đĩ mẹ mày đánh đĩ mới ra được từng chữ mà thk chó hoang =))=))=))",
" # anh đốt pháo hoa r anh nhét pháo vô lồn mẹ mày cho nó nổ tung cháy xém lông lồn mà khiếm khuyết buồng trứng luôn cơ á  😝 👎",
" # Mẹ Mày Bị Cha Đụ Từ Nam Vào Đến Bắc Mà 🤪 👊",
" # vào 10 năm trước t bắt cóc con đĩ mẹ mày t làm nô lệ tình dục để kiếm tiền cho t đi bar quẩy bay lắc cái lỗ lồn con đĩ mẹ mày mà =)))",
" # con mẹ m bị t đưa qua campuchia t dí điện cho muốn quy tiên luôn đó thằng chó 🧐 🤙",
" # Lêu Lêu thk óc chó chỉ bt nhìn t đầu độc Mẹ nó mà Ko Làm Được  😝 👎",
" # bị tao khủng bố nên phải chui xuống lòng đất sống với giun sán à  =))",
" # m là con đĩ đầu đinh giết má để loạn luân với bố mà con khốn",
" # trc a thấy con đĩ mẹ mày nó đứng ở ngã ba đường trần duy hưng làm gái cho mấy thằng cặc già địt lấy tiền mua sách giáo khoa cho m đó =)))",
" # tin t sút vỡ cặc rách dái con đĩ cha dương của m k á 🤣",
" # thằng vô sinh bị anh dẵm nát 2 túi tinh =))=))=))",
" # con lồn ngu này đi cái xe đạp ghẻ của con cụ nó để lại cho nó từ đời con cụ nó còn làm gái bú cu cho trai lấy tiền mà🤣",
" # con chó ngu này bị cả lớp cô lập vì đánh rắm trong lớp khiến cả trường bị khí độc màu da cam từng lỗ đít của nó làm quy tiên cả trường 🤣🤣",
" # thk ngu bị nhiễm phóng xạ trong 1 lần a thả khí độc vô phòng ngủ của nó=))=))=))",
" # con mẹ mày bị anh đụ cho ói ỉa lìa trần quy tiên luôn mà",
" # mẹ mày mà không liếm cặc cho tao thì sẽ bị tao cầm rìu bổ lồn ra đó 🥵👎",
" # chị gái mày phải banh háng ra để tao đút quả bí đao vô mà 🫵😁",
" # tao dùng cái máy kéo ti tao kéo dãn cái vú thối của con mẹ mày xệ như quả mướp luôn mà thằng chó êy🥴🤙",
" # tin tao đụ mẹ mày đến chết luôn không thằng súc vật kia ơi 🤣👌",
" # súc vật cay cú đang cố gắng cứu lấy con mẹ và con chị bị anh em tao đụ tả tơi đụ đến mức thân tàn ma dại kìa ae 🫵🥺",
" # tội nghiệp con chó hoang đang cố phản kháng trong vô vọng 🥺👌",
" # anh đụ mẹ với chị mày chán rồi anh sẽ bắt cóc vợ mày anh đụ nữa nha 🥵💦",
" # chị gái cùng cha khác mẹ của m địt nhau với tao nhiệt tình lắm nè thằng súc sinh ơi 👉👌💦💦",
" # tao cầm cả cái tháp ép phen tao thông thẳng vô lỗ đít con ny mày mà em 🥵💦",
" # cái thằng lgbt giả gái nghiệt súc bị tao xúc phạm cho cay muốn treo cổ tự tử kìa ae 🫵🤣",
" # tức anh muốn đầu thai chuyển kiếp luôn hả thằng óc vật 🥱",
" # ai cho mày đầu thai vậy con chó 🥴😘",
" # anh là diêm vương diệt bọn đĩ đú mà con điếm thúi óc cặc như mày mà ơ ơ ơ 🤣",
" # anh vắt tinh trùng mày cho thằng cụ già của mày uống mà 🫵😂",
" # thằng tộc châu phi bị đá nát sọ nằm bất động dưới bãi cứt =))",
" # cali ăn cứt cay cha m à=))",
" # thk ngu bán dâm cho mấy con lồn già vú nhăn đi lấy tiền vô net chat với cha m hả=))",
" # anh dập nát 2 túi tinh trùng của mày như máy dập rõ mà 👌",
" # cái con óc chó ảo war bổ túc đúc súc vật như mày có trình ăn bố à con đĩ lồn tật 🥱",
" # nhào vô cắn nhau đi con cặc tật nguyền kia 🤣👎",
" # thằng óc cặc như mày làm gì đủ trình thừa kế ADN của bố đâu con 🤣",
" # anh đụ mẹ mày bằng bao cao su mà 🥺",
" # bố của mày là 1 con chó ngao tây tạng đó thằng óc chó 🫵😂",
" # thằng này ăn và khen chubin anh singu khen ngon quá=))",
" # thằng đầu đinh ở nhà mái tôn lấy lá chuối đắp lồn mơ ước được ở nhà cao cửa rộng =))",
" # cả họ nhà mày phải xếp hàng lần lượt bú dái t mà🤣🤣",
" # cả gia đình m bị t sỉ vả cho đến mức thắt cổ tự tử mà =))=))=))",
" # mẹ đẻ của mày giao phối với con chó ngao tây tạng nên mới đẻ được cái thứ súc vật như mày mà con chó điếm  🤣🤙",
" # cái lồn mẹ mày tật nguyền đến mức đẻ ra sản phẩm lỗi của con người vậy cơ à 🗿🤟",
" # thằng óc chó trăn chối điều cuối cùng gì trước khi anh cầm đao phủ anh rã vô não chó mày cho mày tử vong không á 😁🤟",
" # ê cái con súc sinh chó đẻ này đang cố vùng vẫy trước khi anh hành quyết chém đầu con đĩ mẹ mày à mọi ngừi 😁👆",
" # thằng ảo war bị tao chửi cố gắng phản kháng nhưng nút home k cho phép mày cay quá đập cmn máy 🤣👈",
" # Sống như 1 con chó ngu dốt như lũ phèn ói chợ búa cầm dao múa kiếm",
" # Cha mày hóa thân thành hắc bạch vô thường cha mày bắt hồn đĩ mẹ mày xuống chầu diêm vương",
" # Nghèo bần hèn bị cha mày đứng trên đạp đầu lũ đú chúng mày cha đi lên",
" # con má mày tới tháng là lại phun nước máu lồn cho thk cha dượng mày uống",
" # thằng cha làm ăn xin của m phải cất công tích lũy 10 năm mới mua được cái điện thoại ghẻ cho m lên đây xàm lồn với cha m dko =))=))=))",
" # Con điếm phò mã bị cha mày cầm cái cây chà bồn cầu cha chà nát lồn mày nè",
" # con phò điếm này lên mạng tạo nét nhưng quên coi ngày lại gặp đúng anh anh dí cho nát lồn đầu thai 9 kiếp =))=))=))",
" # ngoài mặt tỏ ra bình thường chứ trong lòng đang tức tối và lên kế hoạch quân tử trả thù 10 năm chưa muộn với t đó =))=))=))",
" # tin t chọi cứt vô họng m cho m nghẹt thở vì cứt tràn lan trong cơ thể k em=))=))",
" # bí ngôn nên ăn cắp ngôn của cha mày để đú lại à🤣👈",
" # a chửi m tới tấp cho đến khi m xuống suối vàng uống canh mạnh bà nhưng vẫn đéo thể quên những câu a chửi =))=))=))",
" # a chửi m tới tấp cho đến khi m xuống suối vàng uống canh mạnh bà nhưng vẫn đéo thể quên những câu a chửi =))=))=))",
" # t chạy máy lu t lu bẹp dí cái lồn con đĩ mẹ m mỏng như tờ giấy cho m khỏi thèm nha em =)))",
" # người yêu nó bị t chém đứt đầu xong t còn bắt làm nô lệ tình dục cho con chó nhà t =))",
" # mẹ nó khen cặc t to và chấp nhận li dị với ba nó vì ba nó bị yếu sinh lí =))",
" # cha nó ôm hận t lắm chỉ biết đứng ôm cặc khóc trong vô vọng=)))",
" # thằng óc chó phế vật này có trình sủa mxh k v 🤣",
" # con bướm trâu bị gái có cu yêu qua mạng trap=)))",
" # trăng kia ai vẽ mà tròn loz con mẹ m bị ai địt mà mòn 1 bên 🤣",
" # mẹ m tình nguyện làm búp bê tình dục cho con chó nhà anh nó thỏa mãn để có tiền cứu lấy thk cha già đang bị bệnh tim hấp hối sắp chết của m đó 😏",
" # mẹ m thì xóc lọ cho t còn người ta thì kính lão đắc thọ",
" # m tin bố lấy yamaha bố đề số 3 bố tông vào loz cn đĩ mẹ m k",
" # m gặp các anh đây toàn đấng tối cao a cầm con dao a đâm a thọc a chọc vào cái lỗ loz cn mẹ m mà 🤣👈",
" # cha m lấy gạch ống chọi nát cái đầu mu lồn mẹ mày giờ con bẻm đú",
" # con mồ côi mày mà rớt là tao lấy chiếc xe rùa t cán lòi mu lồn mẹ m đó gán trụ nha",
" # cú đấm sấm sét của anh đủ để ấm nát cái lồn mẹ thằng chó đú nhây như mày🤣👈",
" # cú đá cuồng phong đá bung cái lồn mẹ mày nè thằng não cặc🤣👈",
" # anh lấy cái ô tô anh đâm thẳng dô cái lồn con gái mẹ thằng súc vật như m",
" # hôm nay anh sẽ thay trời hành đạo anh cạo nát cái lông lồn con gái mẹ mày đó nghe chưa",
" # anh đẹp trai hai mái quay qua bên trái đái nát dô cái bàn thờ gái mẹ nghe hong con dog=))",
" # con đĩ eo di bi ti bị mẹ mày hành cho tới đột quỵ k có tiền lo t//ang lễ phải quỳ qua háng tao van xin tao cho tiền đúng kh",
" # thằng cặc chứng kiến cái cảnh mẹ nó bị t cầm bật lửa đốt từng cộng lông bướm:)))",
" # Anh gõ chết con đĩ mẹ mày giờ mày sủa ngôn có st tý coi em nhìn em phèn dạ anh mày chửi luôn ông bà mày đái lên mặt mày nè con sút vật yếu kém",
" # thằng óc cặc bị tao ném xuống ao nhưng béo quá bị chết chìm🐕",
" # mày bị tao hành hung cho sắp đột tử rồi kêu con đĩ mẹ mày qua cứu vãn mày không là tao cho mày nằm quan tài lắng nghe tiếng khóc của gia đình m đó =))",
" # t cho m về với đất mẹ , nơi mà con mẹ đẻ của mày tập tành làm đĩ tối ngày banh háng cho trai đụ =))",
" # cay anh lắm rồi nhưng chỉ bất lực đến thế thôi =))=))=))",
" # thằng cha dượng m bị t sử dụng tuyệt kĩ liên hoàn cước t sút cho cha m xuống âm phủ quỳ lạy diêm vương tha mạng vì kiếp trước lỡ chém chết con gái mẹ á =))",
" # sủa nhanh nhẹn lên tí đi con chó lồn đít khắm=))",
" # t đụ con mẹ m đến mức con mẹ m hóa thành ma da nhảy xuống nước để rồi đéo siêu thoát được khỏi nhân gian =))",
" # cạn bã của XH mà tưởng mình hay hã con thú🤣💨",
" # thằng óc dái bị anh tống vô tù vì tội sát sinh con đĩ má nó =))",
" # t sát sinh cả gia phả nhà m mà em êy",
" # thằng đĩ chó đẻ mặt cặc bất hiếu súc sinh tật nguyền 😂🤣🤣 cái thằng ảo mạng đĩ con mẹ cụ tổ cha mả mẹ cả tổ tiên dòng họ con đĩ cha cụ tật cặc nhà mày bú cặc thằng cai ngục dưới địa ngục mãi mới đẻ được thằng đầu cặc óc chó bất hiếu như m à em",
" # con đĩ bố mày địt liệt cả tinh hoàn bắn nát cặc ra tinh mới đẻ được thằng mặt đĩ chó đẻ như mày hả thằng bất hiếu rách 😂🤣🤣👆👆 , thằng não chó súc sinh cụ tổ con đĩ mẹ mày bị chôn dưới 18 tầng địa ngục nè thằng bất hiếu chó đẻ vô dụng bất tài 😂😂🤣🤣",
" # thằng đĩ cặc nhà mày mẹ đĩ cụ mày đẻ rách lồn bắn nước bướm cạn nước bọt mới đẻ được lũ súc sinh như mày hả 🤣🤣",
" # bố con mẹ m còn địt con cụ m thk óc lợn ba vạn ngu lồn ơi cái thứ mồ côi không nơi nương tựa óc lồn cặn bã =))) ",
" # thk não tật mà quyền lực hạn hẹp ngôn từ khuyết tật như con cặc thk cha dượng nó ấy 😂",
" # Thk mặt cặc khiếm khuyết tinh trùng , thằng đĩ cha mày bắn tinh nổ cả dương vật , khiếm khuyết cả 2 hòn dái vô cái lỗ lồn con đĩ bà già nhà mày mãi mà chỉ đẻ được thứ súc sinh phế vật óc cặc đú đởn như mày hả cái thứ phế vật trần gian",
" # thk óc lợn bị bố mày chửi cho khuyết tật thị giác luôn ae ạ 👊 🤣 ",
" # thằng óc lợn này cay bố mày quá liệt cả tinh hoàn à cái thứ đĩ điếm sĩ đời đầu thai 9 kiếp vẫn chưa hết sĩ , con đĩ cha m thk cặp kè với mấy con lồn già u80 để nuôi nấng m hả thk ngu👊 😎",
" #  cái thứ cave óc lồn đú đởn ngôn thì rẻ mạt🤣🔥",
" #  cái ngôn rẻ rách mang về cùng nải chuối xanh + thêm con gà khỏa thân mang lên bàn thờ tổ tiên mà cúng cho con đĩ mẹ quá cố của cái loại súc vật óc tật như mày đi thằng lồn mồ côi=)))",
" #  con chó nhà tao chính là thủ phạm đã địt nát cái lỗ lồn con mẹ mày khiến cho bà ấy phải đột quỵ vì mất quá nhiều nước lồn nè thằng óc cặc bất hiếu không cứu nổi con bà già nhà mày hả 🤣🤣😁😁🥺",
" # con lgbt ngu phải đi ăn xin tinh trùng để kiềm nén cơn nứng khi không còn mẹ để địt 😂😱😱🫵🔥",
" # con mồ côi này chắc cay anh vì anh đã chém chết thằng cha nó trong 1 lần say sỉn anh đã nhân cơ hội cầm dao bổ nát 2 quả dái dập luôn bộ ấm chén của thằng cha nó",
" # cái thằng đĩ làm trai bao để nuôi ông bà già đang hấp hối ở cái nhà rách nghèo nàn bị anh chà đạp nên , anh nhổ cục nước miến vô họng cái thứ rác rưởi ăn hại như mày nha thằng đĩ hốc hại =)))",
" # tao còn lôi xác con bà già mày lên để tao lấy máy rung châu âu tao nhét vô cái lỗ lồn nhăn nheo cho đến khi nước lồn được bắn ra lần cuối và tao mang xác chết của con đĩ mẹ mày tao ném xuống sông cho mày vớt lên =)))",
" # Đến lúc con mẹ mày được nhét vô trong quan tài thì tao lại đào lên và vắt dái ra đái vô mồm lồn con đĩ mẹ mày =))",
" # cái bọn tật nguyền này chửi ngu như bị máy rung dập lồn nhau vậy các em , anh đây chuyên gia vớt xác mấy con chó đẻ chúng mày để anh ỉa vô cái họng thối nát của mày mà em",
" # anh trù mày ra đường bị xe công ten nơ tông nát sọ phọt cái óc lồn mày ra đường cho chó liếm láp sạch sẽ thì thôi =))",
" # cái thứ dơ bẩn đến từng tế bào da thịt , dơ từ trong tâm hồn dơ ra đến thể xác , thối nát đến nỗi con ruồi còn pk đột tử khi ngửi mùi lồn của mày á thằng phế vật mxh =)))",
" # con lồn này ra đường mày phải bú lấy bú để nước lồn của những con chó vô tôi rồi mày đi làm ăn trộm ăn cắp để mưu sinh qua kiếp nạn nghèo khổ rồi từ đó mày bị tao tống vô ngục để đánh đập và chà đạp như 1 con chó bị bỏ đói 10 ngày =)))",
" # bị điên dại khi thấy anh bắn tinh tràn lồn con mẹ nó và nó bị trói 1 cái bất lực nhìn mẹ bị người khác đụ , kiếp này mày sẽ bị anh chà đạp đến mức phải tự sát và anh sẽ trôn mày xuống dưới đống cứt của con chó nhà anh =))",
" # anh sẽ nhét miếng bả chó vô họng mày để tiễn mày sang thế giới bên kia đoàn tụ với mẹ ruột của mày , con mẹ mày bị anh đụ cho tắc thở nằm la liệt dưới sàn nhà hấp hối kêu cứu mà sao mày không cứu vậy thằng bất hiếu =))",
" # cái lồn con đĩ má mà thứ óc cặc mồ côi ngôn chửi =))=))=))=))=))=))=))=)) ",
" # con chó còn biết giao phối r đẻ con để duy trì nòi giống , còn cái thứ hốc hại của dân như mày chỉ biết bú trinh tiết con đĩ mẹ mày để tồn tại  trên cõi đời lẻ oi này và sĩ đời cùng  với bao khổ đau nỗi uất ức khi thằng cha mày bị tao đạp dập 2 quả cà 🤣🤣🤣",
" # con chó hoang bị anh cầm xà beng anh thông vô cái đốt trĩ của nó =))=))=))🤣",
" # suy nghĩ của con ngu sau khi nó bị tao sỉ nhục kiểu : quân tử trả thù 10 năm chưa muộn =)))))",
" # cú sốc đầu đời của con chó hoang là khi gặp anh và nghe anh chửi =))",
" # thằng đú đởn mời ae nó sang nhà đụ bà già nó free vì hôm nay là ngày cha dượng nó mới qua đời=))",
" # thằng cặc bị tao hạ đo ván sau 1 cú sút ngoạn mục đến từ vị trí của anh =)))",
" # t xuất tinh ngập lồn con chị m mà =))",
" # mẹ mày bị tao địt rách màn trinh mà🤪  ",
" #  tao còn cắt luôn cái ống đái của thằng cha mày để suốt cõi đời còn lại ông ta chỉ có thể nhìn tao địt toét lồn con mẹ mày mỗi đêm =))=))=))=))=))",
" # anh là vua có quyền chà đạp lên bọn súc vật không biết điều =)))",
" # 🤭🤭thk hốc hại định trộm sổ đỏ của bà già để bú lồn con bạn thân =))=))=))",
" # nhà thằng đú này nghèo không có tiền chơi gái nên phải loạn luân luôn với mẹ nó để giải khát cơn thèm thuồng",
" # anh bắt quả tang mày thèm buồi nên địt nhau với chó cảnh nha =))",
" # m có cảnh k đó thằng óc chó não cặc khuyết tật 2 quả dái",
" # địt con gái mẹ m quanh đủ hướng đông tây nam bắc rồi đầu thai sang kiếp mới để tiếp tục bị a đụ mà =)))",
" # anh sỉ vả cả gia phả nhà mày đến mức ông cố nội của mày không chịu được mà treo cổ tự vẫn khi có đứa cháu phế vật không biết phản kháng như m =))=))=))",
" # thằng bất tài vô dụng sủa mạnh lên đi chứ",
" # con súc vật này bị cả xã hội kì thị vì bất hiếu mà =))=)",
" # con đĩ này có quyền tự do ngôn luận đéo đâu mọi ng =))",
" # thk cali ngu lồn",
" # bú cặc tokuda hăng say thế cơ =))",
" # thằng lồn ngu dốt ăn hại núp váy đàn bà rồi nghĩ mình ngầu=))",
" # t cầm máy cưa t cưa đôi chẻ nửa cái lồn má mày ra t đem bán cho chợ đen lấy tiền đóng viện phí cho m đó ",
" # bị t chửi cho nhập viện mà =))",
" # cú sock đầu đời của thk óc cặc mới lên lớp 6",
" # m nhập viện thì anh m lén tiêm thuốc độc vào trong ống chuyền máu của m cho m ngưng thở luôn =)))",
" # t quăng m đăng xuất khỏi trái đất bay lên mặt trăng cho m tắc thở chết trong hư vô",
" # mẹ m qua đời là do t cho bà ấy uống thuốc trừ sâu =)))",
" # mày đàn ông hay đàn bà yếu đuối vậy hả cn chó hoang =))=))=))",
" # con chó đầu đinh bị anh cầm cái đinh ba a thọc vào lỗ nhị nó mà ae =))",
" # thằng con chó quỳ xuống liếm từng bãi nước đái , ăn từng cục cứt tao đi e",
" # quỳ xuống liếm cặc cho cha lẹ đi",
" # Nghe Cha Chửi Chết Con Gái Mẹ Mày Nè Con Ngu",
" # t cầm cây búa t đóng đinh rã vào sọ thằng cha sinh mẹ đẻ của mày đó em =))",
" # Mẹ Mày Bị Tao Lấy Phóng Lợn Chọt Dô Mu Lồn Khi Đang Đi Làm Gái Ở Ngã 3 Trần Duy Hưng🤣",
" # con mẹ m nghe tin m loạn luân vs bố m nên lấy dao cắt cổ tự tử r kìa con ngu =))",
" # m tìm câu nào sát thương tí được k thằng nghịch tử đâm bố đụ mẹ =)) 🤣",
" # đĩ cụ tổ thằng cha nhà mày con điếm lồn thúi mốc , còn cái thằng óc vật sủa ẳng không nên câu đang chết yểu đằng kia là cái thứ mồ coi bị bỏ rơi ngoài bãi rác được anh nhặt về tra tấn rồi anh còn đạp vô cái dái trâu của nó anh bắt nó phải quỳ xuống liếm lồn con bò r địt nhau với con trâu đến mức nó cạn kiệt tinh trùng và phải qua đời trong sự đau đớn khi con cặc của nó vẫn đang cắm vô cái lồn bò =)))",
" # s m cứ nhét cái cặc thối tha của m vô cái lỗ đít con mẹ m v hả cái thứ thèm tinh dịch =))=))=))=))",
" # xạo lồn với t là t chém m bất động luôn đó",
" # sủa hăng lên đi ơ",
" # nhanh nào con điếm =))",
" # cái địt con đĩ cụ mày=}",
" # cả nhà mày súc vật đến nỗi địt nhau trên cái bàn thờ ông công gia phả súc sinh nhà mày à con chó rách 🤣😂😂",
" # bọn tứ tri tật nguyền óc bại =))",
" # đĩ mẹ thk ngu bị anh chửi nhớ cha nhớ mẹ nhớ kiếp trước kìa😹😹😹",
]

MESSAGES_NU = [
    "# lô lô cái con óc lồn",
    "# lồn mẹ m cắn đi con điếm thúi =))",
    "# cầu nguyện gia tiên trước khi chửi t chưa em",
    "# con phò ngu thèm bú cu chó ơi =))",
    "# t cắt dái tk cha dượng m cho m khỏi bú cặc nha em =))",
    "# con ngu nứng thèm cu cha dượng",
    "# cay cú t quá hả con đương kim tiểu thư lượm rác =))",
    "# con cave bị t nói trúng tim đen nên giật bắn mình à =))",
    "# loại cave quái thai như m có chét 100 tấn phấn vô mặt cũng k trắng lên nổi=))",
    "# cay cú t khi con đĩ mẹ m bị t dập lồn à =))",
    "# m tính đóng phim 2 mẹ con bất lực nằm nhìn anh hàng xóm đụ tung 2 cái lồn à",
    "# cái lồn con đĩ má m =))",
    "# con phò rẻ tiền ơi =))",
    "# não con đĩ như m lag hơn wifi công cộng giờ cao điểm mà =))",
    "# m rẻ hơn bó rau muống 5k ngoài chợ nữa đko em =))",
    "# con đĩ phá hoại hạnh phúc ra đình ngkhac =))",
    "# t nói đúng quá m hoảng hốt đko",
    "# sao kh ngông như lúc đầu nữa đi =))",
    "# m tính bú cu ông già để lấy tiền về nuôi cha dượng đang đột quỵ ở nhà đko =))",
    "# cái con bán hoa banh háng đòi chửi t à",
    "# dùng tuyệt chiêu ưỡn lồn ra lấy tiền mua ip mà chat với cha m đi em",
    "# 1 ngày m hút 150l tinh dịch của cha dượng m đko con đĩ =))",
    "# m chửi câu nào là bốc mùi cave câu đó mà",
    "# có trình k thế cái con điếm lồn mốc =))",
    "# lồn thì ghẻ toàn dòi với nhộng =))",
    "# nay đụ được nháy nào với dượng yêu dấu của m chưa cave ngu =))",
    "# cave ngu thèm cu cay t kìa kkk",
    "# m chat quần què gì vậy con bê đê chuyền giới =))",
    "# m là cú có gai mà đko em",
    "# hồi đi học cấp 1 bị bạn bè bắt nạt nên phải trộm tiền bà già bay qua thái chuyền giới để thành con gái banh lồn ra cho bạn đụ để k bị bắt nạt nữa đko =))",
    "# anh đoán chuẩn quá nên lồn m rỉ nước rõ mà em=))",
    "# cái con bướm tràn tinh chưa chùi mà đòi chat với bố à con cave",
    "# m mất trinh từ khi t cầm máy rung nhét lồn m t rung lồn m toét ra nước đko",
    "# clm con đĩ bán dâm lấy tiền vô net chat với t kìa mọi người =))",
    "# nói chuyện dẹo dẹo như lưỡi không xương v con phò điếm thúi =))",
    "# cái lồn mốc của m chắc chỉ có tk cha dượng m dám banh ra liếm th nhỉ =))",
    "# con nghèo k 1 xu dính túi êy",
    "# lồn dòi lồn nhộng đéo có quyền tự do ngôn luận đâu =))",
    "# m đéo có cảnh đâu con cave óc",
    "# con tộc dị tật 2 quả vú =))",
    "# vú m bị cha dượng m nó kéo dãn như quả mướp h 1 bên dài 1 bên ngắn hả =))",
    "# m bị đụ cho úng tinh hay gì mà chat ngu như con cặc vậy =))?",
    "# bán dâm ghen tị được sống trong nhà cao cửa rộng kìa =)))",
    "# con phò bán lồn cho trai đụ ở nhà mái lá túp lều =))",
    "# 1 túp lều tranh 2 trái tim vàng với cha dượng của m đko kkk =))",
    "# m thèm cặc dượng đến mức đầu độc mẹ ruột đến tắc thở rồi đường đường chính chính bú cu cha dượng mà con óc lồn =))",
    "# m đứng đường ở cột giao thông cọ lồn vô cột thì bị csgt cầm baton vụt vô lồn đko =))",
    "# con ngu bị t đạp cho khuyết tật buồng trứng",
    "# sau này m sinh con thì con m nó bị tật nguyền thiểu năng =))",
    "# con cave như m bị t tử hình nên van xin tha tội giết mẹ đẻ để địt cha dượng đko",
    "# quỳ xuống liếm lông chân cho t đi con đĩ",
    "# m giỏi mút nách mút buồi cho cha m lắm mà ơ =))",
    "# m bảo m liếm chân cho t m lại chê à =))",
    "# nay lợn lại chê cám =))",
    "# con nứng ôm hận t vì t dập nát cặc cha dượng nó h nó k có cái để bú =))",
    "# m ra ngã ba trần duy hưng đứng thì bị t tái công ten nơ cán bể lồn phọt ruột ra =))",
    "# bố m cấm cản con đường làm gái của m cho m chết đói chết rét cùng cha dượng m nè con đú",
    "# con phò lục thùng rác thấy miếng thịt chó nhà t gặm dở thì hớn hở lượm về cho cha nó nhai xương =))",
    "# bất hiếu ăn cứt ôm hận t hả tr =))",
    "# t đái vô bàn thờ tk cha dượng m mà ơ",
    "# đế ngày cúng viếng mà m k đủ tiền mua hộp bánh mà cúng cha m hả =))",
    "# con bất hiếu k thờ mẹ đẻ nó mà nó đi thờ tk cha dượng nó mới đau =))",
    "# địt cụ m nè con cave mồ côi cha dượng =))",
    "# cả gia phả m uống nước đái chó của con phốc nhà t mà ơ",
    "# nhà m 3 đời 9 kiếp phải làm nô lệ cho dòng tộc nhà t",
    "# con nghèo k đủ tiền mua quan tài cho cha dượng m mà m pk chôn ổng ở bụi chuối năm xưa 2 cha con địt trộm nhau ở đó hả =))",
    "# cái lồn má m chat gì hài v cave ngu =)))",
    "# ở nhà mái lá r lấy lá chuối đắp lồn riếc rồi h ngáo cần luôn hả =))",
    "# ngựa quen đường cũ hay gì h m lại đi cọ lồn vô tay của em rể m v =))",
    "# con súc vật tính cướp luôn chồng của em gái nó =))",
    "# m tính biến em rể của m thành máy xuất tinh xuất vô lồn m đko em",
    "# t cầm đinh ba t xiên lồn m mà con điếm đú war =))",
    "# m ảo tưởng sức mạnh quá m đi vạch lồn ra đường nhảy tung tăng hả",
    "# đụ má hài hước cái cảnh con đĩ này nó liếm dái chó r bú cặc cha sống qua ngày",
    "# sủa đi con đĩ lồn thèm tinh trùng =))?",
    "# loại m 250kg béo hơn chúp bi =))",
    "# m tải ảnh lên fb mà fb nó đéo tải nổi ảnh vì m nặng quá =)))",
    "# r lúc m đứng lên cân m cân thì nó lại hiển thị số điện thoại =))",
    "# t quăng m lên sao thổ cho nó chém đứt khe lồn m nhen con chó hoang =))",
    "# cái lồn má hài =))",
    "# m là con đười ươi chưa tiến hóa thành người mà",
    "# người k ra người mà ngợm k ra ngợm, cái con cave bị đụ lòi lồn như m lm đc cái đéo gì t đâu",
    "# m vừa khỉ lai chó nên giờ m sống trong kí túc xá hội tâm thần phân liệt hả =))",
    "# con óc đi thi giải cave cấp thị xã r mang huy chương về đặt trước bàn thờ cha dượng nó =))",
    "# con đĩ tâm thần sinh ra và lớn lên ở trại trẻ mồ côi",
    "# m chưa dứt được ti mẹ m mà m chat cái đéo gì vs t thế",
    "# trên mạng m đăng vú to hơn cái đầu, ngoài đời nhìn vào còn đéo thấy nhô lên 1 tý nào =))",
    "# con ngu độn vú đòi giao tiếp với loài người =))",
    "# m thèm cặc nên bú cặc chó của từng nhà 1 trong thành phố à =))",
    "# con ngu bị bán qua campuchia xong t lấy chích điện t chích m giật tung lồn=))",
    "# cạo lông lồn trước khi sủa chưa =))?",
    "# lồn khắm lồn khai một mai bị t chôn xuống đất =))",
    "# m bị mẹ đẻ của m bắt cưới tk béo 500kg nên m ghét mẹ m xog m cho bả uống thuốc độc chết tươi đko =))",
    "# con chó ngu bị t đánh bả chó sủi bọt mép ở cầu long biên =))",
    "# cha dượng m trc đánh thuốc kích dục m xong h m bị nứng giai đoạn cuối dkdo =))",
    "# con thú lồn rành bắn nước lồn còn khỏe hơn vòi phun nước công cộng =))",
    "# cha m móc lồn m cho m bắn nước cạn lồn héo quắt người lại=))",
    "# con đú thủ dâm trong phòng ngủ của bố mẹ nó =))",
    "# xả nước lồn ngập cả thành phố đê con óc toàn tinh =))",
    "# vú thì lép như thằng đàn ông =))",
    "# con đú bị dập tung lồn nên về quỳ xuống mộ mẹ đẻ nó xin mẹ nó gánh còng lưng =))",
    "# các cụ trên trời nhìn cảnh nó phải mút tinh sặc tắc thở chết tươi mà cũng đéo gánh nổi =))",
    "# m xấu đau xấu đớn mà tích tiền mua mĩ phẩm làm gì thế =))",
    "# mặt lồn m thà đánh phấn cho chó còn hơn trang điểm cho m =))",
    "# cái con nứng lên nứng xuống nứng trái nứng phải bị đụ lìa trần quy tiên =))",
    "# m bị hiếp dâm cho phọt cả cứt cả đái ra đko",
    "# mỗi lần đến tháng là con nà nó lại phun máu lồn cho cha dượng nó uống =))",
    "# giờ cha dượng nó chết r mà nó vẫn có thói quen phun máu lồn xung quanh mộ cha nó cho cỏ mọc ở mộ héo hết =))",
    "# con bưởi héo vú nhăn đầu lồn ăn vạ khi t tông bà già nó chết lâm sàn ngoài đường =))",
    "# con súc sinh bị sát sinh =))",
    "# súc vật mỗi lần gặp nạn là rành lồn ra cho cả thiên hạ đút cặc vô để được bảo kê =))",
    "# m chuẩn bị banh háng cho anh hot war nào đút đầu buồi vô lồn m xong nó xuất tinh để nó bảo vệ m khỏi bị t chửi đko con điếm phò =))",
    "# con ngu cầu cứu đi kkkk",
    "# hết đường chạy là cọ lồn vô tưởng để tường mòn r trốn t tiếp hả =)))",
    "# con cave trốn trại ra đây sủa đổng với cha m =))",
    "# cái lồn mẹ m bị t chặt làm đôi mà =))",
    "# còn gì trăn chối trước khi t chặt đầu m k con thú =))",
    "# cái con ngu lồn chưa gỡ khăn quảng đỏ khỏi cổ mà đòi sủa với bố à =))",
    "# m chậm chậm là cả gia phả m trên thiên đường bị t dáng xuống địa ngục tra tấn đó con chó",
    "# kkk cái con mồ côi cha mẹ từ bé giờ đây đã được 1 nhà nông nhận nuôi =))",
    "# ai ngu đi giao cho m cái pe để m sủa trên mxh như con thú thế này",
    "# con đĩ mẹ m đánh đĩ kiếp trước h đủ tiền mua adr ghẻ cho m chat đko =))?",
    "# cả nhà m có truyền thống cave cấp quốc gia à =))",
    "# lồn m còn to hơn cái cửa sổ nhà t nữa đó =))",
    "# 100 con cặc của 100 thk già thi nhau bắn tinh vô lồn con béo này=))",
    "# bắn kiệt tinh cũng k lấp đầy lồn của con thú này đc",
    "# lồn rộng để cha đẻ nó chui vô ở =))",
    "# trước cha đẻ nó bị tử hình mà cha nó trốn khỏi trại được xong cha nó chui tạm vô lồn con chó này để trú ẩn tạm thời =))",
    "# cha đẻ nó thử thách 24h ở trong lồn con này =))",
    "# cha đẻ của nó trước bốc thuốc uống mà bốc nhầm cứt chim nên tinh trùng ổng bị tật mới đẻ ra cái con quái thai này =))",
    "# m bị t đạp sập cầu sập cồng nên vô sinh luôn r đko",
    "# nhân cơ hội nó bị vô sinh nên nó địt thỏa thích =))",
    "# m pk cảm ơn t vì t đã làm m vô sinh nên m k có con chứ m mà k vô sinh là m đẻ con như cái máy r =)))",
    "# m là bình chứa tôn cho toàn nhân loại đúng k",
    "# đến con AI nó còn phải sợ sức chứa tinh của cái lồn m đó con cave =))",
    "# 20 năm sau m bật khóc khi nhớ lại m đã từng làm cave để kiếm cơm manh áo =))",
    "# cave biện minh hay thế =))",
    "# m bị t phong ấn lồn lại nên h thèm tinh muốn chết đko",
    "# cố gắng lên em êy",
    "# sủa hết skill của m ra đây cho t coi nào",
    "# cái ngôn ngữ óc lồn của m khiến cho con AI còn muốn từ chối hiểu =))",
    "# đĩ mẹ m cái con bán dâm cọ lồn để cầu nguyện win t =))",
    "# mẹ m bú cặc cho t để m được vô sàn war đko =))",
    "# mà m mới rank đồng sàn war mà căng với ai v con điếm",
    "# khi nào mới làm người như t đc thế ?",
    "# con cave suốt ngày phá hoại hạnh phúc gia đình ngkhac như m lmj có căn cước công dân =))",
    "# đến nhà nước còn phải từ chối cấp căn cước công dân cho m vì nghĩ m đéo phải con người mà con thú ey",
    "# trước cha đẻ m bị t lừa tiền bán công ti giờ đi lượm ve chai với ăn xin ngoài đường kìa",
    "# nhà m tán gia bại sản khi bị t toxic cho đến chết =))",
    "# con đú chat = nokia đòi ẳng với cha =))",
    "# cái ngữ con thú còn dùng nhà vệ sinh công cộng để ỉa như m làm cái đéo gì có trình chat với t v em =))",
    "# nhà nước ban hành chặt đầu con đĩ lồn cave như m để tránh bú cu người dân vô tội mà =))",
    "# t bê cây cột điện lên t thông vô lồn m cho m tử vong chơi chơi nha",
    "# =)) chó ăn cứt bị sỉ nhục nên mất luôn liêm sỉ cố gắng phản kháng trong vô vọng",
    "# đang cố gắng tỏ ra bình thường mà bị t chửi cho lồn run rỉ cả nước tràn lan vô mồm thk cha dượng nó =)))",
    "# t nói đúng nên m dãy đko",
    "# dãy nhiều vào r t sẽ cho m biết như nào là ăn cứt thay cơm =))",
    "# dãy trong nồi cháo nấu cặc cha của m đi kkk",
    "# t đến đây để đưa m tờ giấy báo tử của ông cố nội m vì ổng đói quá ăn nhầm bả chó mà =))",
    "# theo điều luật của bộ giáo dục và đào tạo thì con đĩ vô danh như m xứng đáng bị treo cổ trước toàn trường cấp 1 =))",
    "# tép tôm vừa bơi ra biển lớn thì bị t lượm mang về xào =))",
    "# cái con ếch ngồi đáy giếng chó chui gầm trại như m thì làm được trò con bò gì v em",
    "# con vô gia cư bán dâm cho mấy tk già nó bắn tinh ngập lỗ mũi =))",
    "# tai m chét tinh còn mắt m bị chột hay gì mà cha chửi m k nghe =))",
    "# clm con chó hoang đòi ăn lại t trong khi nó đang chat với t = máy tính quán net nó vừa đi làm đĩ đc 6k mang vào net chat 1 tiếng=))",
    "# con đĩ mẹ m bị t vả cho phọt não ra đường mà ấy ơi",
    "# con mắt chột đùi ghẻ tay chân toàn ghét 100day k tắm =))",
    "# nhìn bộ dạng thảm hại của m mà t thấy thương cho mẹ đẻ m mất 9 tháng 10 ngày lại đẻ ra cái củ cặc như m =))",
    "# tinh trùng tk bố m bị tật hay gì mà đẻ ra m thế",
    "# m sủa = cả tính mạng đi nào ơ",
    "# cố gắng độ 9 kiếp người để win t nha con súc vật =))",
]

# Hàm show typing animation
async def show_typing_animation(duration, prefix=""):
    end_time = asyncio.get_event_loop().time() + duration
    for ch in itertools.cycle(['.  ', '.. ', '...']):
        if asyncio.get_event_loop().time() > end_time:
            break
        sys.stdout.write(f"\r{prefix}[Typing] Đang soạn{ch}")
        sys.stdout.flush()
        await asyncio.sleep(0.5)
    sys.stdout.write("\r" + " " * 60 + "\r")

# Hàm spam Discord (đổi tên thành discord_spam_worker)
async def discord_spam_worker(token, channel_id, delay, mention_ids, color, semaphore, messages):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    typing_url = f"https://discord.com/api/v10/channels/{channel_id}/typing"
    send_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    mention_text = " ".join([f"<@{uid}>" for uid in mention_ids]) if mention_ids else ""

    async with aiohttp.ClientSession() as session:
        while True:
            for msg in messages:
                try:
                    await semaphore.acquire()
                    await session.post(typing_url, headers=headers)
                    await show_typing_animation(delay, prefix=color)

                    full_msg = f"{msg} {mention_text}" if mention_text else msg
                    async with session.post(send_url, json={"content": full_msg}, headers=headers) as resp:
                        if resp.status == 200:
                            print(f"{color}[OK] Gửi vào kênh {channel_id}: {msg}")
                        else:
                            print(f"{color}[LỖI {resp.status}] {await resp.text()}")
                except Exception as e:
                    print(f"{color}[LỖI] Token gặp lỗi: {e}")
                    await asyncio.sleep(2)
                    gc.collect()
                finally:
                    semaphore.release()


class SpamChoiceView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id

    @discord.ui.button(label="♂️Nam", style=discord.ButtonStyle.primary)
    async def nam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(f"❌ Bạn không có quyền sử dụng lệnh này, xin vui lòng liên hệ <@{admin_id}>.", ephemeral=True)
        await interaction.response.send_modal(NhayDisModalCustom(messages=MESSAGES_NAM, title="Tool war Discord (Nam)"))

    @discord.ui.button(label="♀️Nữ", style=discord.ButtonStyle.danger)
    async def nu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(f"❌ Bạn không có quyền sử dụng lệnh này, xin vui lòng liên hệ admin <@{admin_id}> .", ephemeral=True)
        await interaction.response.send_modal(NhayDisModalCustom(messages=MESSAGES_NU, title="Tool war Discord (Nữ)"))


# Modal tùy biến, truyền messages vào
class NhayDisModalCustom(discord.ui.Modal):
    def __init__(self, messages, title="Tool war Discord"):
        super().__init__(title=title)
        self.messages = messages

        self.token = discord.ui.TextInput(
            label="⚡Token (Nhập token discord của bạn)",
            style=discord.TextStyle.paragraph
        )
        self.channel_id = discord.ui.TextInput(
            label="⚡Channel IDs (nhập id kênh cần spam)"
        )
        self.delay = discord.ui.TextInput(
            label="⚡Delay (giây)"
        )
        self.mention_ids = discord.ui.TextInput(
            label="⚡ID Người cần tag (Không bắt buộc)", required=False
        )

        self.add_item(self.token)
        self.add_item(self.channel_id)
        self.add_item(self.delay)
        self.add_item(self.mention_ids)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚀 Đang tạo tab war...")
        try:
            tokens = [t.strip() for t in self.token.value.strip().split(",") if t.strip()]
            channel_ids = [c.strip() for c in self.channel_id.value.strip().split(",") if c.strip()]
            delay = float(self.delay.value.strip())
            mention_list = (
                [i.strip() for i in self.mention_ids.value.split(",")]
                if self.mention_ids.value else []
            )
            discord_user_id = str(interaction.user.id)
            start_time = datetime.now()
            semaphore = asyncio.Semaphore(1)

            tasks = []
            for token in tokens:
                for channel_id in channel_ids:
                    task = asyncio.create_task(
                        discord_spam_worker(
                            token=token,
                            channel_id=channel_id,
                            delay=delay,
                            mention_ids=mention_list,
                            color=f"[{discord_user_id}] ",
                            semaphore=semaphore,
                            messages=self.messages
                        )
                    )
                    tasks.append(task)

            async with NHAYDIS_LOCK:
                if discord_user_id not in user_nhaydis_tabs:
                    user_nhaydis_tabs[discord_user_id] = []
                user_nhaydis_tabs[discord_user_id].append({
                    "session_count": len(tokens),
                    "channels": channel_ids,
                    "delay": delay,
                    "start": start_time,
                    "tasks": tasks,
                    "messages": self.messages
                })

            await interaction.followup.send(
                f"✅ Đã tạo `{len(tokens) * len(channel_ids)}` tab spam cho <@{discord_user_id}>:\n"
                f"• Kênh: `{', '.join(channel_ids)}`\n"
                f"• Mention: `{', '.join(mention_list) if mention_list else 'Không'}`\n"
                f"• Delay: `{delay}` giây\n"
                f"• Bắt đầu lúc: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: `{e}`")
  


@tree.command(name="taballnhaydis", description="Quản lý/dừng tất cả các phương thức nhây Discord")
async def taballnhaydis(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="🚫 Không có quyền",
            description=f"Bạn không có quyền sử dụng bot, vui lòng liên hệ <@{admin_id}>.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    discord_user_id = str(interaction.user.id)
    async with NHAYDIS_LOCK:
        tabs = user_nhaydis_tabs.get(discord_user_id, [])

    if not tabs:
        embed = discord.Embed(
            title="❌ Không có tab spam",
            description="Bạn không có tab spam Discord nào đang hoạt động.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    # Danh sách tab spam
    embed = discord.Embed(
        title="📋 Danh sách tab spam Discord",
        description="Các tab spam hiện tại của bạn:",
        color=discord.Color.blurple()
    )

    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])

        # Xác định đối tượng dựa theo messages
        if "messages" in tab:
            if tab["messages"] == MESSAGES_NAM:
                target = "Nam"
            elif tab["messages"] == MESSAGES_NU:
                target = "Nữ"
            else:
                target = "nhây 2c hoặc sớ discord"
        else:
            target = "Mặc định"

        embed.add_field(
            name=f"#{idx} | Delay: {tab['delay']}s | Đối tượng: {target}",
            value=f"Kênh: {', '.join(tab['channels'])}\nUptime: {uptime}",
            inline=False
        )

    embed.set_footer(
        text="➡️ Nhập số thứ tự của tab muốn dừng hoặc nhập 'All' để dừng tất cả (trong vòng 30s)."
    )
    await interaction.response.send_message(embed=embed)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏱️ Hết thời gian",
            description="Bạn không nhập kịp, không có tab nào bị dừng.",
            color=discord.Color.orange()
        )
        return await interaction.followup.send(embed=embed)

    c = reply.content.strip()

    # Nếu nhập All → dừng tất cả
    if c.lower() == "all":
        async with NHAYDIS_LOCK:
            for tab in list(tabs):
                for task in tab["tasks"]:
                    task.cancel()
            user_nhaydis_tabs.pop(discord_user_id, None)

        embed = discord.Embed(
            title="⛔ Đã dừng tất cả tab",
            description="Toàn bộ tab spam Discord đã được dừng.",
            color=discord.Color.red()
        )
        return await interaction.followup.send(embed=embed)

    # Nếu nhập số → dừng tab tương ứng
    if not c.isdigit():
        embed = discord.Embed(
            title="⚠️ Không hợp lệ",
            description="Bạn phải nhập số thứ tự hoặc 'All'. Không dừng tab nào.",
            color=discord.Color.yellow()
        )
        return await interaction.followup.send(embed=embed)

    i = int(c)
    if not (1 <= i <= len(tabs)):
        embed = discord.Embed(
            title="⚠️ Số không hợp lệ",
            description=f"Vui lòng nhập số từ 1 đến {len(tabs)}.",
            color=discord.Color.yellow()
        )
        return await interaction.followup.send(embed=embed)

    # Dừng tab theo số
    async with NHAYDIS_LOCK:
        chosen = tabs.pop(i - 1)
        for task in chosen["tasks"]:
            task.cancel()
        if not tabs:
            del user_nhaydis_tabs[discord_user_id]

    embed = discord.Embed(
        title="⛔ Tab spam đã dừng",
        description=f"Bạn đã dừng thành công **tab số {i}**.",
        color=discord.Color.red()
    )
    await interaction.followup.send(embed=embed)


# Hàm show typing animation
async def show_typing_animation(duration, prefix=""):
    end_time = asyncio.get_event_loop().time() + duration
    for ch in itertools.cycle(['.  ', '.. ', '...']):
        if asyncio.get_event_loop().time() > end_time:
            break
        sys.stdout.write(f"\r{prefix}[Typing] Đang soạn{ch}")
        sys.stdout.flush()
        await asyncio.sleep(0.5)
    sys.stdout.write("\r" + " " * 60 + "\r")

nhaydis2c = [
    "sủa mau", "con chó", "đú à", "ngu kìa", "sao mếu", "sợ tao", "chó ngu",
    "khóc r", "ăn hại", "phế v", "run à", "khóc ak", "ai cho", "chửi mau",
    "nhanh lên", "slow vậy", "chập mạch", "con ngu", "cay à", "cú kìa",
    "khóc rõ", "hốc hại", "chat mau", "chậm vậy", "mạnh mà", "sao r",
    "bất lực", "khóc lun", "speed đê", "con gà", "mạnh k", "hăng à", "chat lẹ",
    "sao câm", "chạy à", "trốn à", "nhanh đi", "sồn đi", "yếu à", "m ngu",
    "chó phế", "cãi đi", "óc chó", "clm",
]

sodiscord = [
        "# thứ nghiệt súc óc lồn loạn luân với mẹ ruột để tổn tại cái con đĩ mẹ m giao phối với giống súc vật não cặc tật nguyền nào mà đẻ ra đứa quái thai như m á e óc chó bị hiếp dâm đến mức cạn kiệt tinh trùng cái gia phả rẻ rách nhà m nha con óc lồn bị t sỉ vả đến mức tuyệt vòng mà thk ngu kkk bố đạp dập nát 2 túi tinh của m cho m tử vong luôn h thk lồn ngu dốt kkk  thằng óc cặc phế vật này bị đứt mạch máu não nên đột quỵ r à , con lồn già kịch liệt buồng trứng ,  đĩ ngu xuẩn về mà bú trinh tiết con bà già nhà m đi e , thứ ghẻ lồn thối rữa câm họng lại đi , chửi thì ngu óc cặc thì nhiều , đéo biết con mẹ mày đẻ ra mày bất hạnh đến mức nào nữa , cái thứ bất hiếu rẻ rách vô ơn đĩ cha con lồn súc sinh mày nha thứ lăng loàng cave đú đởn, cái lồn má mày nha thằng ngu óc vật gõ cho nhiều vào sau về già khớp tay nó khiếm khuyết thì lại kêu là tại tuổi già , cái giống súc vật này ai lai tạo ra nó vậy ae",
"# cái thằng óc lồn cả đời kh ngóc đầu lên được nó ganh tị với t vì t ở nhà cao cửa rộng còn cái thằng óc chó như nó mãi ở bờ đề gầm cầu với chuột trù gián bẩn =))), thằng lồn bê đê bị vô sinh bẩm sinh nó đang vận khí cầu trời cầu phật cho nó 1 mụ con với bà hàng xóm 90t =)))) cái mả mẹ nhà thằng lồn cào phím lỏ bị cha bắt bài cha xử tỉ m trước pháp luật trần gian r t bắn súng nổ bộ ấm chén của m trước hàng vạn người nha cái thằng súc vật bú cặc cha đẻ =)) ",
"# thằng đĩ chó đẻ mặt cặc bất hiếu súc sinh tật nguyền  cái thằng ảo mạng đĩ con mẹ cụ tổ cha mả mẹ cả tổ tiên dòng họ con đĩ cha cụ tật cặc nhà mày bú cặc thằng cai ngục dưới địa ngục mãi mới đẻ được thằng đầu cặc óc chó đĩ con cặc cha con mẹ mày hả em thằng súc vật chó đẻ não tật mẹ đĩ cặc súc sinh bất hiếu , con đĩ bố mày địt liệt cả tinh hoàn bắn nát cặc ra tinh mới đẻ được thằng mặt đĩ chó đẻ như mày hả thằng bất hiếu rách  , thằng não chó súc sinh cụ tổ con đĩ mẹ mày bị chôn dưới 18 tầng địa ngục nè thằng bất hiếu chó đẻ vô dụng bất tài  thằng đĩ cặc nhà mày mẹ đĩ cụ mày đẻ rách lồn bắn nước bướm cạn nước bọt mới đẻ được lũ súc sinh như mày hả =))",
"# bố con mẹ m còn địt con cụ m thk óc lợn ba vạn  ngu lồn ơi  cái thứ mồ côi không nơi nương tựa óc lồn cặc bã loại thk não tật mà quyền lực hạn hẹp ngôn từ khuyết tật. Thk mặt cặc khiếm khuyết tinh trùng .  thằng đĩ cha mày bắn tinh nổ cả dương vật , khiếm khuyết cả 2 hòn dái vô cái lỗ lồn con đĩ bà già nhà mày mãi mà chỉ đẻ được thứ súc sinh phế vật óc cặc đú đởn như mày hả cái thứ phế vật trần gian , thk óc lợn bị bố mày chửi cho khuyết tật thị giác luôn ae ạ  , thằng óc lợn này cay bố mày quá liệt cả tinh hoàn à cái thứ đĩ điếm sĩ đời đầu thai 9 kiếp vẫn chưa hết sĩ , con đĩ cha m thk cặp kè với mấy con lồn già u80 để nuôi nấng m hả thk ngu ",
"# con đĩ óc vật này có trình chửi nhau không vậy mọi người , cái thứ cave óc lồn đú đởn ngôn thì rẻ mạt, cái ngôn rẻ rách mang về cùng nải chuối xanh + thêm con gà khỏa thân mang lên bàn thờ tổ tiên mà cúng cho con đĩ mẹ quá cố của cái loại súc vật óc tật như mày đi thằng lồn mồ côi , cái thứ khuyết tật tinh trùng nứng cặc suốt ngày địt nhau với mẹ ruột cho đỡ thèm cơn nứng , con chó nhà tao chính là thủ phạm đã địt nát cái lỗ lồn con mẹ mày khiến cho bà ấy phải đột quỵ vì mất quá nhiều nước lồn nè thằng óc cặc bất hiếu không cứu nổi con bà già nhà mày hả, cái thứ phế vật ăn hại này nhìn chán vậy mọi người ",
"# thằng chó ngu phải đi ăn xin tinh trùng để kiềm nén cơn nứng khi không còn mẹ để địt, con mồ côi này chắc cay anh vì anh đã chém chết thằng cha nó trong 1 lần say sỉn anh đã nhân cơ hội cầm dao bổ nát 2 quả dái dập luôn bộ ấm chén của thằng cha nên giờ bố nó bị bê đê và địt nhau với chó 🫵🤣👑🌟 , chốt lại là thằng óc lồn súc sinh chó đẻ phế vật chửi ngu như cái lồn con đĩ mẹ nó và sẽ đéo bao giờ có thể ngóc đầu lên trước cái xã hội này nha cái thứ cặn bã óc lồn thèm tinh trùng chó dái ơi",
"# cái con đĩ chó đẻ này làm con giáp thứ 13 ngu lồn nhất tao từng biết nha =))=))=))=))=))=))=))=))=))=))=))=))=)) , cái thằng đĩ làm trai bao để nuôi ông bà già đang hấp hối ở cái nhà rách nghèo nàn bị anh chà đạp nên , anh nhổ cục nước miến vô họng cái thứ rác rưởi ăn hại như mày nha thằng đĩ hốc hại =))=))=))=))=))=))=))=)) anh là người đã lái xe lạng lách đánh võng và tông chết con bà già nhà mày để rồi bà ấy đã tử vong trong bệnh viện và tao còn lôi xác con bà già mày lên để tao lấy máy rung châu âu tao nhét vô cái lỗ lồn nhăn nheo cho đến khi nước lồn được bắn ra lần cuối và tao mang xác chết của con đĩ mẹ mày tao ném xuống sông cho mày vớt lên =)) ",
"# Đến lúc con mẹ mày được nhét vô trong quan tài thì tao lại đào lên và vắt dái ra đái vô mồm lồn con đĩ mẹ mày =))=))=))=))=))=))=)) cái bọn tật nguyền này chửi ngu như bị máy rung dập lồn nhau vậy các em , anh đây chuyên gia vớt xác mấy con chó đẻ chúng mày để anh ỉa vô cái họng thối nát của mày mà em, anh trù mày ra đường bị xe công ten nơ tông nát sọ phọt cái óc lồn mày ra đường cho chó liếm láp sạch sẽ thì thôi . cái thứ dơ bẩn đến từng tế bào da thịt , dơ từ trong tâm hồn dơ ra đến thể xác , thối nát đến nỗi con ruồi còn pk đột tử khi ngửi mùi lồn của mày á thằng phế vật mxh ",
"# ê con chó đang rên kia ơi=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=)) cái lồn con đĩ mẹ mày thứ óc cặc bú dái chó để sống qua ngày , ra đường mày phải bú lấy bú để nước lồn của những con chó vô tôi rồi mày đi làm ăn trộm ăn cắp để mưu sinh qua kiếp nạn nghèo khổ rồi từ đó mày bị tao tống vô ngục để đánh đập và chà đạp như 1 con chó bị bỏ đói 10 ngày r xong t cho m bại dưới bãi cứt t ỉa ra xong t cho m chứng kiến cảnh cà nhà m chôn thây dưới lời lẽ thâm độc của t nè ",
"# cái thằng hốc hại  bị điên dại khi thấy anh bắn tinh tràn lồn con mẹ nó và nó bị trói 1 cái bất lực nhìn mẹ bị người khác đụ , kiếp này mày sẽ bị anh chà đạp đến mức phải tự sát và anh sẽ trôn mày xuống dưới đống cứt của con chó nhà anh , anh sẽ nhét miếng bả chó vô họng mày để tiễn mày sang thế giới bên kia đoàn tụ với mẹ ruột của mày , con mẹ mày bị anh đụ cho tắc thở nằm la liệt dưới sàn nhà hấp hối kêu cứu mà sao mày không cứu vậy thằng bất hiếu=))=))=))=))=))=))=))=))=))",
"# cái lồn con đĩ má mà thứ óc cặc mồ côi ngôn chửi =))=))=))=))=))=))=))=)) ơii=))=))=))=))=))=))=))=))=))=))=)) đĩ bà già mày cái thứ kém cỏi ăn hại của bố mẹ rồi lên mạng ảo ảo con cặc gì vậy em . mày còn vô dụng hơn cả con chó nữa em =))=))=))=))=))=))=))=))=))=))=))=)) con chó còn biết giao phối r đẻ con để duy trì nòi giống , còn cái thứ hốc hại của dân như mày chỉ biết bú trinh tiết con đĩ mẹ mày để tồn tại  trên cõi đời lẻ oi này và sĩ đời cùng  với bao khổ đau nỗi uất ức khi thằng cha mày bị tao đạp dập 2 quả cà , tao còn cắt luôn cái ống đái của thằng cha mày để suốt cõi đời còn lại ông ta chỉ có thể nhìn tao địt toét lồn con mẹ mày mỗi đêm =))=))=))=))=)) anh là vua có quyền chà đạp lên bọn súc vật không biết điều , ông trời ban cho con cặc để mày địt nhau với chó à thằng lồn ngu dốt ăn hại núp váy đàn bà rồi nghĩ mình ngầu ",
"# đĩ cụ tổ thằng cha nhà mày con điếm lồn thúi mốc , còn cái thằng óc vật sủa ẳng không nên câu đang chết yểu đằng kia là cái thứ mồ coi bị bỏ rơi ngoài bãi rác được anh nhặt về tra tấn rồi anh còn đạp vô cái dái trâu của nó anh bắt nó phải quỳ xuống liếm lồn con bò r địt nhau với con trâu đến mức nó cạn kiệt tinh trùng và phải qua đời trong sự đau đớn khi con cặc của nó vẫn đang cắm vô cái lồn bò =))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=))=)) ",
"# ê thằng cặc già bẩn thỉu , s m cứ nhét cái cặc thối tha của m vô cái lỗ đít con mẹ m v hả cái thứ thèm tinh dịch =))=))=))=))=))=))=))=))=))=)) cái lồn má mẹ mày thèm máu lồn con đĩ cha mày hả cái thứ bê đê bất hiếu , mặt thì bóng loáng như mấy con sinh vật da trơn , lỗ mũi thì thò lò ra cả nhúm lông , chân tay thì ghẻ lên ghẻ xuống , ghẻ luôn cả cái tâm hồn lẫn thể xác =))=))=))=))=))=))=))=)) cái thứ óc cặc bị diêm vương tra tấn , con mẹ mày phải địt nhau với diêm vương để diêm vương tha tội cho thứ vô dụng hốc hại ăn mày như mày hả con đĩ điếm thúi tha =))=))=))=))=))=)) ",
"# tao cầm que củi đụ vô cái lỗ đít dính cứt của con mẹ mày cho mẹ mày qua đời nha thk óc cặc mặt lồn súc vật ăn hại mà còn phế vật nằm la liệt 1 chỗ như người thực vật nè em , cái thứ bất hiếu chó đẻ cặc tật khiếm khuyết tinh trùng óc lồn cặn bã mặt thì bẩn thỉu như cái lồn dính tinh của con đĩ mẹ mày vừa với đụ nhau với chó dái rồi nó bắn tinh vô họng con đĩ mẹ mày nè cái đĩ cha mày nha thằng phế vật ",
"# cả nhà m chết dưới tay của t mà con chó ngu =)), thằng lồn mặt buồi bị t dí tới tấp chạy về mếu với cha nội nó xong nghĩ kế quân tử trả thù 10 năm chưa muộn, 10 năm sau nó làm công nhân xây dựng biệt thự cho tao thì bị tao chôn dưới nền xi măng của nhà, đến lúc mày đéo siêu thoát được thì con đĩ mẹ mày lại là người phải mặc rạp ra bái lạy tổ tiên giúp m siêu thoát khỏi nhân gian, nhưng tao đéo cho mày siêu thoát mà t cầm bazuka t bắn nổ não linh hồn thối rữa của m ra, đến lúc m làm ma làm quỷ thì bị t tống vô ngục tối chịu uất ức và chà đạp 1000 năm ảnh sáng =)))) ",
"# thằng lồn ngu hút buồi sặc tinh bất tỉnh nhân sự bị tao ỉa cứt chọi vô xác m trong xe tang lạnh lẽo của con đĩ mẹ mày thì tao triệu hồi jack 97 quẩy tung nóc quan tài m ra t đái vô xương cốt của đĩ má m cho m ôm hận t 9 kiếp còn lại nhưng đéo làm được gì, =))) thằng lồn bú trinh bf già u80 để tiếp tục được sống trong vô vọng =)), ước mơ trở thành dân war của m bị t đá bay đi ngay khi m làm trò xiếc khỉ trước mặt tao mà cái thằng đầu buồi ăn cứt uống đái bú tục lói phét =)) ",
"# m còn chiêu thức gì mới hơn không cứ nhìn m chat ngu như con chó liếm lồn bò mà còn cái con đĩ mẹ quá cố của m bj t sát hại nên m ôm hận t nhưng đéo làm được đầu buồi gì nên chỉ biết khấn bái lạy trời ban cho sức mạnh chửi win a m nhưng thứ m được ban là cục cứt cóc =))), mỗi lần đến tháng là con đĩ mẹ m lại phun máu lồn cho m giải khát nhưng h t giết bả r nên m k còn gì chỉ biết khóc lóc ôm lồn đĩ mẹ m r nức nợ hực hợ đúng không thằng nứng cu bắn tinh lên bia mộ mẹ đẻ để giải tỏa cơn thèm lồn giai đoạn cuối =))) ",
"# clm thằng đú bị hiv sẩy mụn cặc vì địt nhau quá 180 kiếp =))) cái thằng cha m nó ôm hận t vì t giết chết con bà m vì cả nhà m có truyền thống loạn luận mẹ và con mà đúng kh thằng vô danh ăn cứt , chó dại hoang tàn cali bú buồi sặc cặc =)) cả lò m địt nhau tê buồi rách lồn còn đến đời m thì thất truyền vì m bị vô sinh giai đoạn cuối k thể sinh con nên m tính bắt cóc con của ngkhac mang về cho mẹ vợ xem để bả thương bả còn cho m ở lại nhà =))) ",
"# thằng vô gia cư đang cố xây cái rì sọt lều nhà mái lá để ở =))), ngu còn nghèo lần đầu t thấy cái thứ cóc ghẻ mà đòi oai như m đó thk adr óc chó chat ngu như con đĩ mẹ m nó đánh đĩ ở trần duy hưng xong bị t phóng xe hơi tông lủng lồn rách trinh qua đời ở ngã ba tdh, thằng trai bao ngu lồn bị bỏ đói 10 ngày cay cha quá hóa rồ đi cắn lồn con chó cái r liếm mu chó =))), mồ côi cay cú vì bị t nói trúng tim đen nên giờ đang loay hoay dở trò con bò ra tính biện minh cho bản thân vì tao nói quá đúng nên giật bắn mình lên =)) ", 
"# thằng vô danh câm mõm r hay sao v hay m bị t đá rụng quai hàm gãy 23 cái răng xong h thành thằng món tật nguyền đi ăn xin tinh trùng của con chó =)), con đĩ mẹ m là bồn chứa tinh cho toàn nhân loại xong h đẻ ra cái thằng đú war 2025 ngu lồn bị nút cặc ngay khi làm trò con bò đko thằng em mồ côi cha mẹ, m còn k bt bố đẻ m là ai vì mẹ m địt nhiều thằng quá nên loạn con mẹ nó ADN mà =))), con thú bú lồn cha đẻ như m chỉ biết dãy dụa trước cái chết cận kề khi thằng cha m đi làm từng đồng từng cắt còn m ở nhà m nhàm cặc trên mạng xã hội thì bj t dạy đời cho quê muốn đội quần hello kity vô não chó nhà m chứ cái thằng ngu bị chửi cho đứt mạch mãu não tai biến cmnr đko óc lồn =))",
"# t chét xi măng vô lồn con đĩ má m cho nó nghẹt thở lồn chết con bà nó chứ còn cái thằng hốc hại bú dái chó liếm lồn trâu nhặt lá đá ống đồng suốt ngày bứt lá xung nhét kẽ răng như m thì làm được cái con cặc gì cho đợi không thế thằng ngu lồn não úng tinh dái khiếm khuyết còn vô danh vô dụng như con đĩ má m nó bị t chặt đầu chặt xác ra còn đang phân hủy dưới sông bạch đằng nơi t sát hại bà ấy bằng thuốc diệt chuột thì lúc đó m đang bận xem sex sục cặc chéo với thằng bạn thân mà k biết mẹ m đã từ trần dưới tay tao =))))",
"# đĩ mẹ m thằng chó vô học bị t chà đạp lên thân thể xong mỗi đêm tự dày xéo bản thân đế chết lìa trần quy tiên xong mắt m trợn ngược lên nằm yên giấc ngàn thu trên bàn thờ cạnh di mộ con đĩ mẹ m , thằng lồn trâu bị t quẳng xuống sông chết đuối vì quá béo, m nặng 170kg cả bỉm cả cứt mà đko con chó ngu bị sỉ vả đến mức tắc thở chết k nhắm mắt =))))",  
"# con đĩ mẹ m phải quỳ xuống bú cặc liếm tinh cho t để m được vào sàn mà m vẫn phế như chó đẻ vậy hả thằng ngu ăn cứt gà uống đái chó, cái thằng đĩ cụ tổ nhà m nó thất vọng vì có 1 thằng cháu đã vô sinh còn vô dụng như m nên ổng thắt cổ tự tử luôn r kìa thằng đú phế ỉa ơi, m gõ mãi mới ra 1 câu vậy hả con đĩ mẹ m, đít tắc cứt nên gõ k lại cha đúng kh con thú đú war ngu si tứ tri óc vật =)))",
"# cả nhà m bị t lôi cổ ra chém chết chỉ vì thời chiến tranh của vn kháng chiến chống thực dân pháp ng ng nhà nhà oai hùng đi đánh giặc còn con đĩ mẹ m sợ quá phải banh háng móc lồn ra cho giặc địt để được tha mạng nên hôm nay cả nhà m bị t tuyên tán tử hình chém đầu phóng hỏa chết chui chết lùi , chết không nhắm mắt chết không nguyên vẹn mà chết đéo được chôn kkk thằng ngu ạ",
"# m còn cái cặc gì mới mẻ hơn cái ngôn sứt vỡ của m k vậy cái thằng ngu nứng cu sục buồi hút tinh sặc nước lồn con đĩ bà m bị t cầm đinh ba xiên lồn qua đời trên giường bệnh h bả nằm ở nhà xác khoa nhi bệnh viện mà k thể siêu thoát khi có đứa cháu phế vật như mày mà cái thằng mồ côi chó đẻ ăn hại mọi vùng miền, t gõ vừa nhanh vừa gọn còn m gõ như đánh rắm vào mặt cả nhà m thế con thú hoang vô sinh vô giác ơi, m đéo biết chat thì m bật con mắt m lên full HD mà coi t chat chửi đột quỵ cả dòng tộc m luôn nè thằng đầu buồi mặt cặc",
"# m làm trai bao kiếm tiền mưu sinh nuôi cả lò m trong khi đó thì t nhà cao cửa rộng chứ ai nhà mái lá như thằng cặc ghẻ tiết kiệm tiền cả năm được cái adr ghẻ đòi chat với cha m thì bị cha dập cho nát cặc khiếm khuyết 2 hòn dái lở của m ra cho ông m liếm sạch, m k chat lại cha thì m vạch quần ông già m ra bú cặc sặc tinh để lớn đi nhé cái thằng đầu trâu mặt ngựa",
"# t chửi m mà h đơ người liệt dây thần kinh não thần hồn nát thần tính xong m trầm cảm đến mức m bị bb cô lập r xa lánh vì nói xàm cặc nhảm 3 xàm 9 vạn con đĩ mẹ m chết kh nhắm mắt vì m gây nên nỗi ô nhục lớn 9 kiếp cx k quên được đó thằng chó vô gia cư ở nhà lá đá ống bơ, cả nhà m phải làm trò hề cho nhân loại để được tồn tại trên thế giới này nếu không t giết cả nhà m t hỏa táng từng đứa t mang tro cốt t đổ cho chó nhai xương dòng tộc nhà m",
"# m bị câm hả m thấy t chat nhanh chưa mà m chậm như con rùa bò vậy thằng ngu này, con đĩ má m mang nặng đẻ đau lồn rách háng mà đẻ ra cái thằng cn hốc hại ăn bám lại còn bê đê cấp mãn tính như m mà bả muốn độn thổ xuống âm phủ để cho đỡ nhục ấy con chó giống não lồn bị cha chà đạp cho nhồi máu cơ tim mà qua đời trên sàn war của tao nè ",
"# m mỏi tay hay m chat k nổi mà lề mề như con sên vậy, m dậy chat đi con đĩ mẹ m nó bị t địt cho liệt buống trứng đang cấp cứu ở bệnh viện phải nằm truyền nước lồn kia kìa thằng ngu ngục ơi, t tống m vô song sắt ngồi ăn cơm tù nhìn cảnh t đụ mẹ m lìa trần ỉa ra quần nè cái thứ súc sinh ăn cơm trên bàn thờ ông địa r bị giật điện qua đời ở tuổi 13 =))",
   ]    
      
async def discord_spam_worker_all(token, channel_id, delay, mention_ids, color, semaphore, messages):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    typing_url = f"https://discord.com/api/v10/channels/{channel_id}/typing"
    send_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    mention_text = " ".join([f"<@{uid}>" for uid in mention_ids]) if mention_ids else ""

    async with aiohttp.ClientSession() as session:
        while True:
            for msg in messages:
                try:
                    await semaphore.acquire()
                    await session.post(typing_url, headers=headers)
                    await show_typing_animation(delay, prefix=color)

                    full_msg = f"{msg} {mention_text}" if mention_text else msg
                    async with session.post(send_url, json={"content": full_msg}, headers=headers) as resp:
                        if resp.status == 200:
                            print(f"{color}[OK] Gửi vào kênh {channel_id}: {msg}")
                        else:
                            print(f"{color}[LỖI {resp.status}] {await resp.text()}")
                except Exception as e:
                    print(f"{color}[LỖI] Token gặp lỗi: {e}")
                    await asyncio.sleep(2)
                    gc.collect()
                finally:
                    semaphore.release()


class SpamVuiceView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id

    @discord.ui.button(label="Sớ discord", style=discord.ButtonStyle.secondary)
    async def so_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                f"❌ Bạn không có quyền sử dụng lệnh này, xin vui lòng liên hệ <@{admin_id}>.", ephemeral=True
            )
        await interaction.response.send_modal(AllDisModalCustom(messages=sodiscord, title="Sớ Discord"))

    @discord.ui.button(label="2c discord", style=discord.ButtonStyle.secondary)
    async def dis2c_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                f"❌ Bạn không có quyền sử dụng lệnh này, xin vui lòng liên hệ <@{admin_id}>.", ephemeral=True
            )
        await interaction.response.send_modal(AllDisModalCustom(messages=nhaydis2c, title="2c Discord"))

    @discord.ui.button(label="Nhây idea", style=discord.ButtonStyle.secondary)
    async def idea_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                f"❌ Bạn không có quyền sử dụng lệnh này, xin vui lòng liên hệ <@{admin_id}>.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📌 Chọn đối tượng",
            description=(
                "- Vui lòng chọn đối tượng cần spam 🗣️"
            ),
            color=discord.Color.orange()
        )

        view = SpamChoiceView(owner_id=interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)







# Modal tùy biến, truyền messages vào
class AllDisModalCustom(discord.ui.Modal):
    def __init__(self, messages, title="All Discord"):
        super().__init__(title=title)
        self.messages = messages

        self.token = discord.ui.TextInput(
            label="⚡Token (Nhập token discord của bạn)",
            style=discord.TextStyle.paragraph
        )
        self.channel_id = discord.ui.TextInput(
            label="⚡Channel IDs (nhập id kênh cần spam)"
        )
        self.delay = discord.ui.TextInput(
            label="⚡Delay (giây)"
        )
        self.mention_ids = discord.ui.TextInput(
            label="⚡ID Người cần tag (Không bắt buộc)", required=False
        )

        self.add_item(self.token)
        self.add_item(self.channel_id)
        self.add_item(self.delay)
        self.add_item(self.mention_ids)

async def on_submit(self, interaction: discord.Interaction):
    await interaction.response.send_message("🚀 Đang tạo tab war...")
    try:
        tokens = [t.strip() for t in self.token.value.strip().split(",") if t.strip()]
        channel_ids = [c.strip() for c in self.channel_id.value.strip().split(",") if c.strip()]
        delay = float(self.delay.value.strip())
        mention_list = (
            [i.strip() for i in self.mention_ids.value.split(",")]
            if self.mention_ids.value else []
        )
        discord_user_id = str(interaction.user.id)
        start_time = datetime.now()
        semaphore = asyncio.Semaphore(1)

        tasks = []
        for token in tokens:
            for channel_id in channel_ids:
                task = asyncio.create_task(
                    discord_spam_worker(
                        token=token,
                        channel_id=channel_id,
                        delay=delay,
                        mention_ids=mention_list,
                        color=f"[{discord_user_id}] ",
                        semaphore=semaphore,
                        messages=self.messages
                    )
                )
                tasks.append(task)

        async with NHAYDIS_LOCK:
            if discord_user_id not in user_nhaydis_tabs:
                user_nhaydis_tabs[discord_user_id] = []
            user_nhaydis_tabs[discord_user_id].append({
                "session_count": len(tokens),
                "channels": channel_ids,
                "delay": delay,
                "start": start_time,
                "tasks": tasks,
                "messages": self.messages
            })

        # Tạo embed thông báo
        embed = discord.Embed(
            title="✅ Đã tạo tab spam discord thành công",
            description=f"Thông tin chi tiết về task spam của <@{discord_user_id}>",
            color=discord.Color.green(),
            timestamp=start_time
        )
        embed.add_field(name="• Số tab", value=f"{len(tokens) * len(channel_ids)}", inline=True)
        embed.add_field(name="• Kênh", value=", ".join(channel_ids), inline=True)
        embed.add_field(name="• Mention", value=", ".join(mention_list) if mention_list else "Không", inline=True)
        embed.add_field(name="• Delay", value=f"{delay} giây", inline=True)
        embed.set_footer(text="Bắt đầu lúc")
        embed.timestamp = start_time

        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed_error = discord.Embed(
            title="❌ Lỗi khi tạo tab spam",
            description=f"`{e}`",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed_error)


# Slash command chính
@tree.command(name="allnhaydis", description="Tạo tab spam chửi idea trên Discord")
async def allnhaydis(interaction: discord.Interaction):
    # ✅ Kiểm tra quyền
    if not has_permission(interaction):
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng bot")

    admin_id = 1310263571434704988  # ID admin
    embed = discord.Embed(
        title="📜 Chọn phương thức",
        description=(
            "- Vui lòng chọn 1 phương thức trong số phương thức nhây sau đây🗣️\n"
            "- dùng lệnh /taballnhaydis để dừng bot spam⛔\n"
        ),
        color=discord.Color.blue()
    )
     # ✅ Truyền owner_id là ID người gõ lệnh
    view = SpamVuiceView(owner_id=interaction.user.id)

    await interaction.response.send_message(
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions(users=True)
    )






    
def telegram_send_loop(token, chat_ids, caption, photo, delay, stop_event, discord_user_id):
    while not stop_event.is_set():
        for chat_id in chat_ids:
            if stop_event.is_set():
                break
            try:
                if photo:
                    if photo.startswith("http"):
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        data = {"chat_id": chat_id, "caption": caption, "photo": photo}
                        resp = requests.post(url, data=data, timeout=10)
                    else:
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        with open(photo, "rb") as f:
                            files = {"photo": f}
                            data = {"chat_id": chat_id, "caption": caption}
                            resp = requests.post(url, data=data, files=files, timeout=10)
                else:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    data = {"chat_id": chat_id, "text": caption}
                    resp = requests.post(url, data=data, timeout=10)

                if resp.status_code == 200:
                    print(f"[TELE][{discord_user_id}] Gửi thành công → {chat_id}")
                elif resp.status_code == 429:
                    retry = resp.json().get("parameters", {}).get("retry_after", 10)
                    print(f"[TELE][{discord_user_id}] Rate limit {retry}s")
                    time.sleep(retry)
                else:
                    print(f"[TELE][{discord_user_id}] Lỗi {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                print(f"[TELE][{discord_user_id}] Exception: {e}")
            time.sleep(0.2)
        time.sleep(delay)
        

@tree.command(
    name="treotele",
    description="Treo ngôn telegram"
)
@app_commands.describe(
    tokens="Token Telegram bot (ngăn cách dấu phẩy)",
    chats="ID nhóm chat (ngăn cách dấu phẩy)",
    text="Nội dung tin nhắn",
    delay="Delay giữa mỗi lần gửi (giây)",
    img="Link ảnh đính kèm (tuỳ chọn)"
)
async def treotele(
    interaction: discord.Interaction,
    tokens: str,
    chats: str,
    text: str,
    delay: int,
    img: str = None
):
    # ✅ Phân quyền
    if not has_permission(interaction):
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng bot")

    await interaction.response.defer()

    tokens_list = [t.strip() for t in tokens.split(",") if t.strip()]
    chats_list = [c.strip() for c in chats.split(",") if c.strip()]

    if delay < 1:
        return await interaction.followup.send("❌ Delay phải lớn hơn 1 giây")

    valid = []
    for tk in tokens_list:
        try:
            resp = requests.get(f"https://api.telegram.org/bot{tk}/getMe", timeout=5)
            if resp.ok:
                valid.append(tk)
            else:
                await interaction.followup.send(f"⚠️ Token không hợp lệ: `{tk}`")
        except requests.exceptions.ConnectTimeout:
            await interaction.followup.send(f"⚠️ Không thể kiểm tra token `{tk}`: kết nối Telegram bị timeout, vẫn cho phép chạy")
            valid.append(tk)  # ✅ vẫn cho chạy
        except Exception as e:
            await interaction.followup.send(f"⚠️ Lỗi kiểm tra token `{tk}`: `{e}`")

    if not valid:
        return await interaction.followup.send("❌ Không có token hợp lệ")

    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    for tk in valid:
        stop_event = multiprocessing.Event()
        process = multiprocessing.Process(
            target=telegram_send_loop,
            args=(tk, chats_list, text, img, delay, stop_event, discord_user_id),
            daemon=True
        )
        process.start()

        with TREOTELE_LOCK:
            user_treotele_tabs.setdefault(discord_user_id, []).append({
                "process": process,
                "stop_event": stop_event,
                "start": start_time,
                "token": tk,
                "chats": chats_list,
                "text": text,
                "img": img,
                "delay": delay
            })

    await interaction.followup.send(
        f"✅ Đã tạo tab treo Telegram cho <@{discord_user_id}>:\n"
        f"• Chats: `{', '.join(chats_list)}`\n"
        f"• Tokens: `{len(valid)}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Ảnh: `{img or 'Không có'}`\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
                
@tree.command(
    name="tabtreotele",
    description="Quản lý/dừng tab treo telegram"
)
async def tabtreotele(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")

    discord_user_id = str(interaction.user.id)
    with TREOTELE_LOCK:
        tabs = user_treotele_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab treo telegram nào đang hoạt động")

    msg = "**Danh sách tab treo telegram của bạn:**\n"
    for i, tab in enumerate(tabs, 1):
        elapsed = int((datetime.now() - tab["start"]).total_seconds())
        uptime = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        msg += (
            f"{i}. Token:`{tab['token'][:10]}...` | Chats:`{','.join(tab['chats'])}` | "
            f"Delay:`{tab['delay']}`s | Up:`{uptime}`\n"
        )
    msg += f"\nNhập số tab để dừng tab"

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào")

    choice = reply.content.strip()
    if not choice.isdigit():
        return await interaction.followup.send("Không dừng tab nào")
    idx = int(choice)
    if not (1 <= idx <= len(tabs)):
        return await interaction.followup.send("Số không hợp lệ")

    with TREOTELE_LOCK:
        tab = tabs.pop(idx-1)
        tab["stop_event"].set()
        if not tabs:
            user_treotele_tabs.pop(discord_user_id, None)

    return await interaction.followup.send(f"Đã dừng tab số {idx}")
    


def parse_cookie_str(cookie_str):
    return dict(item.strip().split('=') for item in cookie_str.split(';') if '=' in item)

def spam_loop(acc_id):
    info = SPAM_TASKS.get(acc_id)
    if not info:
        return

    cl = info["client"]
    targets = info["targets"]
    message = info["message"]
    delay = info["delay"]

    while True:
        for target in targets:
            if target in info["stop_targets"]:
                continue
            try:
                if target.isdigit():
                    cl.direct_send(message, thread_ids=[target])
                else:
                    user_id = cl.user_id_from_username(target)
                    cl.direct_send(message, [user_id])
                print(f"[+] Gửi thành công tới: {target}")
            except Exception as e:
                print(f"[!] Lỗi gửi {target}: {e}")
        time.sleep(delay)

@tree.command(name="treoig", description="Treo spam IG bằng sessionid")
@app_commands.describe(
    cookie="Cookie Instagram (chỉ cần chứa sessionid=...)",
    targets="Danh sách username hoặc thread ID, phân cách dấu phẩy",
    message="Nội dung muốn gửi",
    delay="Delay mỗi vòng (giây)"
)
async def treoig(
    interaction: discord.Interaction,
    cookie: str,
    targets: str,
    message: str,
    delay: float
):
    if str(interaction.user.id) not in ADMIN_IDS:
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng bot.")

    await interaction.response.defer(thinking=True)

    cookie_dict = parse_cookie_str(cookie)
    sessionid = cookie_dict.get("sessionid")
    if not sessionid:
        return await interaction.followup.send("❌ Cookie thiếu sessionid.")

    try:
        cl = Client()
        cl.login_by_sessionid(sessionid=sessionid)
    except Exception as e:
        return await interaction.followup.send(f"❌ Đăng nhập thất bại: {e}")

    target_list = [t.strip() for t in targets.split(",") if t.strip()]
    if not target_list:
        return await interaction.followup.send("❌ Không có username hoặc thread nào.")

    idx = len(SPAM_TASKS) + 1
    stop_set = set()
    spam_info = {
        "thread": None,
        "start_time": datetime.now(),
        "targets": target_list,
        "message": message,
        "delay": delay,
        "client": cl,
        "stop_targets": stop_set
    }

    thread = threading.Thread(target=spam_loop, args=(idx,), daemon=True)
    spam_info["thread"] = thread
    SPAM_TASKS[idx] = spam_info
    thread.start()

    await interaction.followup.send(
        f"✅ Đã bắt đầu spam IG (Tab {idx}):\n"
        f"• Số người nhận: `{len(target_list)}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Thời gian: `{spam_info['start_time'].strftime('%Y-%m-%d %H:%M:%S')}`"
    )

@tree.command(name="tabtreoig", description="Xem và dừng tab đang treo IG")
async def tabtreoig(interaction: discord.Interaction):
    if str(interaction.user.id) not in ADMIN_IDS:
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng bot.")


    if not SPAM_TASKS:
        return await interaction.response.send_message("⚠️ Không có tab IG nào đang chạy.")

    msg = "**📌 Danh sách tab treo IG:**\n"
    for i, (idx, info) in enumerate(SPAM_TASKS.items(), start=1):
        uptime = datetime.now() - info["start_time"]
        msg += (
            f"{idx}. Targets: `{len(info['targets'])}` | Delay: `{info['delay']}s` | "
            f"Up: `{str(uptime).split('.')[0]}`\n"
        )
    msg += "\n🛑 Nhập STT tab muốn dừng (VD: `1`)"

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30)
        stt = int(reply.content.strip())
    except:
        return await interaction.followup.send("⏰ Hết thời gian hoặc nhập sai. Không dừng tab nào.")

    if stt not in SPAM_TASKS:
        return await interaction.followup.send("❌ STT không hợp lệ.")

    task = SPAM_TASKS.pop(stt)
    task["stop_targets"].update(task["targets"])  # stop toàn bộ target
    return await interaction.followup.send(f"✅ Đã dừng tab IG `{stt}`.")

@tree.command(
    name="treogmail",
    description="Treo gmail"
)
@app_commands.describe(
    accounts="Email|Passapp",
    to_email="Email nhận",
    content="Nội dung",
    delay="Delay"
)
async def treogmail(
    interaction: discord.Interaction,
    accounts: str,
    to_email: str,
    content: str,
    delay: float
):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")
    if delay < 1:
        return await interaction.response.send_message("Delay phải trên 1s")

    smtp_list = parse_gmail_accounts(accounts)
    if not smtp_list:
        return await interaction.response.send_message("Không parse được tài khoản")

    discord_user_id = str(interaction.user.id)
    stop_evt = threading.Event()
    start_time = datetime.now()

    tab = {
        "thread": None,
        "stop_event": stop_evt,
        "start": start_time,
        "smtp_list": smtp_list,
        "to_email": to_email,
        "content": content,
        "delay": delay
    }
    thread = threading.Thread(target=gmail_spam_loop, args=(tab, discord_user_id), daemon=True)
    tab["thread"] = thread

    with TREOGMAIL_LOCK:
        user_treogmail_tabs.setdefault(discord_user_id, []).append(tab)

    thread.start()

    await interaction.response.send_message(
        f"Đã tạo tab treo gmail cho <@{discord_user_id}>:\n"
        f"• Tài khoản: `{len(smtp_list)}`\n"
        f"• To: `{to_email}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )    
    
@tree.command(
    name="tabtreogmail",
    description="Quản lý/dừng tab treo gmail"
)
async def tabtreogmail(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")

    discord_user_id = str(interaction.user.id)
    with TREOGMAIL_LOCK:
        tabs = user_treogmail_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab treo gmail nào đang hoạt động")

    msg = "**Danh sách tab treo gmail của bạn:**\n"
    for i, tab in enumerate(tabs, 1):
        up = datetime.now() - tab["start"]
        msg += (
            f"{i}. Accounts:`{len(tab['smtp_list'])}` → `{tab['to_email']}` | "
            f"Delay:`{tab['delay']}`s | Up:`{str(up).split('.')[0]}`\n"
        )
    msg += f"\nNhập số tab để dừng tab"

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id==interaction.user.id and m.channel.id==interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào")

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("Không dừng tab nào")
    idx = int(c)
    if not (1<=idx<=len(tabs)):
        return await interaction.followup.send("Số không hợp lệ")

    with TREOGMAIL_LOCK:
        tab = tabs.pop(idx-1)
        tab["stop_event"].set()
        if not tabs:
            user_treogmail_tabs.pop(discord_user_id, None)

    return await interaction.followup.send(f"Đã dừng tab số {idx}")
    
@tree.command(name="checkcookie", description="Kiểm tra tối đa 5 cookie Facebook")
@app_commands.describe(
    cookie1="Cookie 1 (tùy chọn)",
    cookie2="Cookie 2 (tùy chọn)",
    cookie3="Cookie 3 (tùy chọn)",
    cookie4="Cookie 4 (tùy chọn)",
    cookie5="Cookie 5 (tùy chọn)"
)
async def checkcookie(
    interaction: discord.Interaction,
    cookie1: str = "",
    cookie2: str = "",
    cookie3: str = "",
    cookie4: str = "",
    cookie5: str = ""
):
    if not has_permission(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")

    await interaction.response.defer()

    cookies = [cookie1, cookie2, cookie3, cookie4, cookie5]
    result_lines = []

    for idx, ck in enumerate(cookies, start=1):
        if not ck.strip():
            continue  # Bỏ qua ô trống

        try:
            kem = Kem(ck.strip())
            result_lines.append(f"✅ **CK{idx}** sống → UID: `{kem.user_id}`")
        except Exception as e:
            result_lines.append(f"❌ **CK{idx}** die → `{str(e)}`")

    if not result_lines:
        return await interaction.followup.send("❗ Bạn chưa nhập cookie nào.")

    await interaction.followup.send(
        "**Kết quả kiểm tra cookie:**\n" + "\n".join(result_lines)
    )                   

def spam_sms_forever(phone, stop_event):
    while not stop_event.is_set():
        for fn in functions:
            if stop_event.is_set():
                break
            try:
                fn(phone)
            except Exception as e:
                print(f"[SPAM] Lỗi từ {fn.__name__}: {e}")
            time.sleep(1)

@tree.command(name="treosms", description="Spam OTP SmS")
@app_commands.describe(sdt="Số điện thoại muốn spam")
async def treosms(interaction: discord.Interaction, sdt: str):
    uid = str(interaction.user.id)
    with TREOSMS_LOCK:
        if uid not in TREOSMS_TASKS:
            TREOSMS_TASKS[uid] = []
        for t in TREOSMS_TASKS[uid]:
            if t["sdt"] == sdt:
                await interaction.response.send_message(f"⚠️ Số {sdt} đã được spam rồi")
                return
        stop_event = threading.Event()
        thread = threading.Thread(target=spam_sms_forever, args=(sdt, stop_event), daemon=True)
        thread.start()
        TREOSMS_TASKS[uid].append({"sdt": sdt, "stop_event": stop_event, "start": datetime.now()})
    await interaction.response.send_message(f"✅ Đã bắt đầu spam OTP vào số `{sdt}`")

@tree.command(name="tabtreosms", description="Xem và dừng các số đang spam")
async def tabtreosms(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    with TREOSMS_LOCK:
        tabs = TREOSMS_TASKS.get(uid, [])
    if not tabs:
        await interaction.response.send_message("📭 Không có tab treo SMS nào đang chạy")
        return
    msg = "**Danh sách tab treo SMS của bạn:**\n"
    for i, tab in enumerate(tabs):
        uptime = datetime.now() - tab["start"]
        mins, secs = divmod(uptime.seconds, 60)
        msg += f"{i+1}. `{tab['sdt']}` - Uptime: {mins} phút {secs} giây\n"
    msg += "\nNhập số thứ tự để dừng tab đó (trong vòng 30s)"
    await interaction.response.send_message(msg)
    def check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    try:
        reply = await bot.wait_for("message", timeout=30.0, check=check)
    except:
        await interaction.followup.send("⏰ Hết thời gian")
        return
    idx = reply.content.strip()
    if not idx.isdigit():
        await interaction.followup.send("❌ Không hợp lệ")
        return
    idx = int(idx) - 1
    with TREOSMS_LOCK:
        if 0 <= idx < len(tabs):
            tabs[idx]["stop_event"].set()
            sdt = tabs[idx]["sdt"]
            tabs.pop(idx)
            if not tabs:
                del TREOSMS_TASKS[uid]
            await interaction.followup.send(f"🛑 Đã dừng spam số `{sdt}`")
        else:
            await interaction.followup.send("❌ Không tìm thấy tab")

def parse_cookie_string(cookie_str):
    try:
        cookie_str = cookie_str.strip()
        if cookie_str.startswith("{") and cookie_str.endswith("}"):
            data = json.loads(cookie_str)
        else:
            data = {}
            for part in cookie_str.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    data[k.strip()] = v.strip()

        # Ánh xạ tự động nếu thiếu session_key
        if "session_key" not in data:
            if "zpw_sek" in data:
                data["session_key"] = data["zpw_sek"]

        return data if "session_key" in data else None
    except Exception as e:
        print(f"[!] Lỗi parse cookie: {e}")
        return None

class UserSelectView(discord.ui.View):
    def __init__(self, users, callback, timeout=60):
        super().__init__(timeout=timeout)
        self.callback_fn = callback
        self.add_item(UserDropdown(users, self.callback_fn))

class UserDropdown(discord.ui.Select):
    def __init__(self, users, callback):
        options = [
            discord.SelectOption(label=f"{i+1}. {user}", value=user)
            for i, user in enumerate(users)
        ]
        super().__init__(placeholder="Chọn người nhận để spam...", min_values=1, max_values=len(users), options=options)
        self.callback_fn = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_fn(interaction, self.values)

def get_access_token(corp_id, secret):
    url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}'
    response = requests.get(url).json()
    return response.get('access_token', '')

def send_wecom_msg(token, agent_id, user, msg):
    send_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}'
    data = {
        "touser": user,
        "msgtype": "text",
        "agentid": agent_id,
        "text": {"content": msg},
        "safe": 0
    }
    return requests.post(send_url, json=data)

@tree.command(name="treowechat", description="Spam tin nhắn WeCom lặp vô hạn")
@app_commands.describe(
    corp_id="CORP_ID của WeCom",
    agent_id="AGENT_ID của ứng dụng",
    secret="SECRET API của WeCom",
    delay="Số giây giữa mỗi lần gửi",
    message="Nội dung tin nhắn muốn gửi",
    users="Danh sách người dùng, phân cách bằng dấu | (vd: user1|user2)"
)
async def treowechat(
    interaction: discord.Interaction,
    corp_id: str,
    agent_id: str,
    secret: str,
    delay: float,
    message: str,
    users: str
):
    if not is_admin(interaction) and not is_authorized(interaction):
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này!")

    await interaction.response.defer()

    user_list = [u.strip() for u in users.split("|") if u.strip()]
    if not user_list:
        return await interaction.followup.send("❌ Danh sách người dùng trống!")

    token = get_access_token(corp_id, secret)
    if not token:
        return await interaction.followup.send("❌ Không thể lấy access token!")

    discord_user_id = str(interaction.user.id)
    stop_event = threading.Event()
    start_time = datetime.now()

    def spam_worker():
        while not stop_event.is_set():
            for user in user_list:
                if stop_event.is_set(): return
                try:
                    res = send_wecom_msg(token, agent_id, user, message)
                    if res.status_code == 200:
                        print(f"[✓] Gửi tới {user}: {message}")
                    else:
                        print(f"[×] Lỗi tới {user}: {res.text}")
                except Exception as e:
                    print(f"[!] Lỗi gửi tới {user}: {e}")
                time.sleep(delay)

    th = threading.Thread(target=spam_worker, daemon=True)

    with WECHAT_SPAM_LOCK:
        if discord_user_id not in wechat_spam_tabs:
            wechat_spam_tabs[discord_user_id] = []
        wechat_spam_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "users": user_list,
            "message": message
        })

    th.start()

    await interaction.followup.send(
        f"✅ Đã bắt đầu spam WeCom tới `{', '.join(user_list)}` mỗi `{delay}` giây.\n"
        f"• Tin nhắn: `{message}`\n"
        f"• Số lượng người: `{len(user_list)}`\n"
        f"• Dừng bằng lệnh `/tabwechat` theo STT."
    )


# Bộ nhớ lưu các tab wechat đang chạy
wechat_tabs = {}  # {discord_user_id: [{"thread": th, "stop_event": stop_event, "start": start_time, "to_user": "ID"}]}
WAITING_WECHAT_STOP = {}  # Tạm lưu trạng thái chờ người dùng chọn STT

@tree.command(name="tabwechat", description="Xem & quản lý các phiên spam WeChat")
async def tabwechat(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    await interaction.response.defer()

    if user_id not in wechat_tabs or not wechat_tabs[user_id]:
        return await interaction.followup.send("🔍 Bạn không có tab WeChat nào đang chạy.")

    # Hiển thị danh sách tab đang chạy
    text = "📋 **Danh sách tab WeChat đang chạy:**\n"
    for i, tab in enumerate(wechat_tabs[user_id], 1):
        uptime = datetime.now() - tab["start"]
        uptime_str = str(uptime).split('.')[0]  # bỏ mili giây
        text += f"`{i}`. Đang gửi đến: `{tab['to_user']}` | Uptime: `{uptime_str}`\n"

    text += "\n✏️ Nhập số STT (ví dụ `1`, `2`, `3`) để dừng một tab cụ thể."

    WAITING_WECHAT_STOP[user_id] = True
    await interaction.followup.send(text)

# Lắng nghe tin nhắn tiếp theo từ user để nhận STT
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)

    if user_id in WAITING_WECHAT_STOP:
        content = message.content.strip()
        if content.isdigit():
            index = int(content) - 1

            if user_id in wechat_tabs and 0 <= index < len(wechat_tabs[user_id]):
                tab = wechat_tabs[user_id][index]
                tab["stop_event"].set()
                wechat_tabs[user_id].pop(index)

                await message.channel.send(f"🛑 Đã dừng tab WeChat số `{content}`.")
            else:
                await message.channel.send("❌ STT không hợp lệ!")
        else:
            await message.channel.send("⚠️ Vui lòng nhập **số thứ tự** của tab để dừng.")

        # Dù đúng hay sai, xoá trạng thái chờ
        WAITING_WECHAT_STOP.pop(user_id, None)

    await bot.process_commands(message)        
    
@tree.command(name="treopollzl", description="Treo spam bình chọn Zalo kèm tag")
@app_commands.describe(
    imei="IMEI Zalo",
    cookie="Cookie Zalo (JSON hoặc thô: key=value;...)",
    poll_options="Mỗi dòng là 1 lựa chọn bình chọn",
    delay="Delay giữa mỗi lần gửi (giây)"
)
async def treopollzl(
    interaction: discord.Interaction,
    imei: str,
    cookie: str,
    poll_options: str,
    delay: float
):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này.")

    await interaction.response.defer(thinking=True)

    try:
        with open("nhay.txt", "r", encoding="utf-8") as f:
            questions = [line.strip() for line in f if line.strip()]
    except:
        return await interaction.followup.send("❌ Không tìm thấy file `nhay.txt`!")

    poll_list = [line.strip() for line in poll_options.split('\n') if line.strip()]
    if not poll_list:
        return await interaction.followup.send("❌ Không có lựa chọn nào trong poll_options!")

    cookies = parse_cookie_string(cookie)
    if not cookies:
        return await interaction.followup.send("❌ Cookie không hợp lệ hoặc thiếu `session_key`.")

    from tooltreopoll import Bot
    bot = Bot(imei, cookies)

    groups = bot.fetch_groups()
    if not groups:
        return await interaction.followup.send("❌ Không tìm thấy nhóm nào!")

    group_msg = "**📋 Danh sách nhóm Zalo:**\n"
    for i, g in enumerate(groups, 1):
        group_msg += f"{i}. {g['name']} — `{g['id']}`\n"

    await interaction.followup.send(group_msg[:2000])
    await interaction.followup.send("👉 Nhập STT nhóm muốn gửi poll (VD: `1,2`) trong 30s")

    def check_group(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check_group, timeout=30)
        selected_indexes = [int(x.strip()) for x in reply.content.split(",") if x.strip().isdigit()]
        selected_indexes = [i for i in selected_indexes if 1 <= i <= len(groups)]
    except:
        return await interaction.followup.send("⏱️ Hết thời gian hoặc định dạng không hợp lệ.")

    tag_map = {}

    for idx in selected_indexes:
        group = groups[idx - 1]
        members = bot.fetch_members(group['id'])

        mem_msg = f"👥 Thành viên nhóm **{group['name']}**:\n"
        for i, m in enumerate(members, 1):
            mem_msg += f"{i}. {m['name']} — `{m['id']}`\n"
        await interaction.followup.send(mem_msg[:2000])
        await interaction.followup.send("👉 Nhập STT thành viên cần tag (VD: `1,2`) trong 30s")

        def check_tag(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            reply_tag = await interaction.client.wait_for("message", check=check_tag, timeout=30)
            tag_indexes = [int(x.strip()) for x in reply_tag.content.split(",") if x.strip().isdigit()]
            tag_indexes = [i for i in tag_indexes if 1 <= i <= len(members)]
        except:
            return await interaction.followup.send("⏱️ Hết thời gian chọn tag.")

        tag_users = [members[i - 1] for i in tag_indexes]
        tag_map[group['id']] = {
            'info': group,
            'members': tag_users
        }

    # Khởi động spam poll
    stop_event = threading.Event()
    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    def poll_worker():
        while not stop_event.is_set():
            for group_id, data in tag_map.items():
                group = data['info']
                tag_users = data['members']
                for question in questions:
                    if stop_event.is_set():
                        return
                    mention_text = " ".join([f"@{u['name']}" for u in tag_users])
                    poll_text = f"{mention_text} {question}"
                    try:
                        bot.createPoll(question=poll_text, options=poll_list, groupId=group['id'])
                        print(f"📤 Poll đến {group['name']}: {poll_text}")
                    except Exception as e:
                        print(f"❌ Lỗi gửi poll: {e}")
                    time.sleep(delay)

    th = threading.Thread(target=poll_worker, daemon=True)

    with POLL_LOCK:
        if discord_user_id not in user_poll_tabs:
            user_poll_tabs[discord_user_id] = []
        user_poll_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "groups": list(tag_map.keys()),
            "delay": delay
        })

    th.start()

    await interaction.followup.send(
        f"✅ Đã bắt đầu spam poll vô hạn.\n"
        f"• Nhóm: `{len(tag_map)}` nhóm\n"
        f"• Delay: `{delay}`s\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
@tree.command(name="tabpollzl", description="Quản lý/dừng tab spam poll Zalo")
async def tabpollzl(interaction: discord.Interaction):
    if not has_permission(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này.")

    discord_user_id = str(interaction.user.id)
    with POLL_LOCK:
        tabs = user_poll_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("❌ Bạn không có tab poll nào đang chạy.")

    msg = "**📊 Danh sách tab poll của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        groups = ', '.join([f"`{gid}`" for gid in tab["groups"]])
        msg += f"{idx}. 🧾 GroupID(s): {groups}\n   ⏳ Delay: `{tab['delay']}s` | Uptime: `{uptime}`\n"
    msg += "\n👉 Nhập STT tab muốn **dừng** (1 - {}).".format(len(tabs))

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱️ Hết thời gian. Không dừng tab nào.")

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("⚠️ Không hợp lệ.")
    i = int(c)
    if not (1 <= i <= len(tabs)):
        return await interaction.followup.send("⚠️ Số không hợp lệ.")

    with POLL_LOCK:
        chosen = tabs.pop(i - 1)
        chosen["stop_event"].set()
        if not tabs:
            del user_poll_tabs[discord_user_id]

    await interaction.followup.send(f"⛔ Đã dừng tab poll số `{i}`")      

@tree.command(name="nhaytagzalo", description="Spam tag zalo fake soạn")
@app_commands.describe(
    imei="IMEI thiết bị Zalo",
    cookie="Cookie Zalo (JSON hoặc thô: key=value;...)",
    delay="Delay giữa các lần gửi (giây)"
)
async def nhaytagzalo(
    interaction: discord.Interaction,
    imei: str,
    cookie: str,
    delay: float
):
    # ✅ Chặn người không có quyền
    if not has_permission(interaction):
        return await interaction.response.send_message("⛔ Bạn không có quyền sử dụng lệnh này.")

    await interaction.response.defer(thinking=True)

    from toolnhaytagzl import Bot, tag_user_from_nhay, Mention, ThreadType, Message

    def parse_cookie_string(cookie_str):
        try:
            cookie_str = cookie_str.strip()
            if cookie_str.startswith("{") and cookie_str.endswith("}"):
                data = json.loads(cookie_str)
            else:
                data = {}
                for part in cookie_str.split(";"):
                    if "=" in part:
                        k, v = part.strip().split("=", 1)
                        data[k.strip()] = v.strip()
            if "session_key" not in data and "zpw_sek" in data:
                data["session_key"] = data["zpw_sek"]
            return data if "session_key" in data else None
        except Exception as e:
            print(f"[!] Lỗi parse cookie: {e}")
            return None

    cookies = parse_cookie_string(cookie)
    if not cookies:
        return await interaction.followup.send("❌ Cookie không hợp lệ hoặc thiếu session_key.")

    bot = Bot(imei, cookies)
    groups = bot.fetch_groups()
    if not groups:
        return await interaction.followup.send("❌ Không tìm thấy nhóm nào!")

    group_msg = "**📋 Danh sách nhóm Zalo:**\n"
    for i, g in enumerate(groups, 1):
        group_msg += f"{i}. {g['name']} — `{g['id']}`\n"
    await interaction.followup.send(group_msg[:2000])
    await interaction.followup.send("👉 Nhập STT nhóm muốn spam (VD: `1`) trong 30s")

    def check_group(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check_group, timeout=30)
        index = int(reply.content.strip())
        if not (1 <= index <= len(groups)):
            raise ValueError()
    except:
        return await interaction.followup.send("⏱️ Hết thời gian hoặc STT nhóm không hợp lệ.")

    group = groups[index - 1]
    members = bot.fetch_members(group['id'])
    if not members:
        return await interaction.followup.send("❌ Không lấy được danh sách thành viên!")

    mem_msg = f"👥 Thành viên nhóm **{group['name']}**:\n"
    for i, m in enumerate(members, 1):
        mem_msg += f"{i}. {m['name']} — `{m['id']}`\n"
    await interaction.followup.send(mem_msg[:2000])
    await interaction.followup.send("👉 Nhập STT thành viên muốn tag (VD: `1`)")

    def check_member(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check_member, timeout=30)
        member_idx = int(reply.content.strip())
        if not (1 <= member_idx <= len(members)):
            raise ValueError()
    except:
        return await interaction.followup.send("⏱️ Hết thời gian hoặc STT không hợp lệ.")

    target = members[member_idx - 1]
    target_uid = target['id']
    target_name = target['name']
    thread_id = group['id']

    stop_event = threading.Event()
    thread = threading.Thread(
        target=tag_user_from_nhay,
        args=(bot, target_uid, thread_id, target_name, delay, imei, cookies, stop_event),
        daemon=True
    )
    thread.start()

    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    with NHAYTAGZALO_LOCK:
        if discord_user_id not in user_nhaytagzalo_tabs:
            user_nhaytagzalo_tabs[discord_user_id] = []
        user_nhaytagzalo_tabs[discord_user_id].append({
            "thread": thread,
            "stop_event": stop_event,
            "start": start_time,
            "group_name": group['name'],
            "uid": target_uid,
            "target_name": target_name
        })

    await interaction.followup.send(
        f"✅ Bắt đầu spam tag `@{target_name}` mỗi `{delay}`s trong nhóm `{group['name']}`."
    )
    
@tree.command(name="tabnhaytagzalo", description="Xem & dừng các tab spam tag Zalo")
async def tabnhaytagzalo(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)
    with NHAYTAGZALO_LOCK:
        tabs = user_nhaytagzalo_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("❌ Bạn không có tab spam tag Zalo nào đang chạy.")

    msg = "**📌 Danh sách tab nhây tag Zalo của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = str(datetime.now() - tab["start"]).split('.')[0]
        msg += (
            f"{idx}. 👥 Nhóm: `{tab['group_name']}`\n"
            f"   🧑‍💬 Tag: `{tab['target_name']} ({tab['uid']})`\n"
            f"   ⏱️ Uptime: `{uptime}`\n"
        )
    msg += "\n👉 Nhập STT tab muốn dừng (VD: `1`) trong 30s."

    await interaction.response.send_message(msg[:2000])

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check, timeout=30)
        index = int(reply.content.strip())
        if not (1 <= index <= len(tabs)):
            raise ValueError("out of range")
    except:
        return await interaction.followup.send("⏱️ Hết thời gian hoặc STT không hợp lệ.")

    with NHAYTAGZALO_LOCK:
        tab = tabs.pop(index - 1)
        tab["stop_event"].set()
        if not tabs:
            del user_nhaytagzalo_tabs[discord_user_id]

    await interaction.followup.send(f"⛔ Đã dừng tab spam tag Zalo số `{index}`.")

                                                
@tree.command(name="treosticker", description="Treo spam sticker vào nhóm Zalo")
@app_commands.describe(
    imei="IMEI thiết bị Zalo",
    cookie="Cookie Zalo (JSON hoặc thô: key=value;...)",
    delay="Thời gian chờ giữa mỗi lần gửi (giây)"
)
async def treosticker(
    interaction: discord.Interaction,
    imei: str,
    cookie: str,
    delay: float
):
    # ✅ Giới hạn người dùng
    if not has_permission(interaction):
        return await interaction.response.send_message("⛔ Bạn không có quyền sử dụng lệnh này.")

    await interaction.response.defer(thinking=True)

    import json, threading
    from datetime import datetime
    from spamstk import Bot

    def parse_cookie_string(cookie_str):
        try:
            cookie_str = cookie_str.strip()
            if cookie_str.startswith("{") and cookie_str.endswith("}"):
                return json.loads(cookie_str)
            data = {}
            for part in cookie_str.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    data[k.strip()] = v.strip()
            if "session_key" not in data and "zpw_sek" in data:
                data["session_key"] = data["zpw_sek"]
            return data if "session_key" in data else None
        except:
            return None

    cookies = parse_cookie_string(cookie)
    if not cookies:
        return await interaction.followup.send("❌ Cookie không hợp lệ!")

    bot = Bot(imei, cookies)
    groups = bot.fetch_groups()
    if not groups:
        return await interaction.followup.send("❌ Không tìm thấy nhóm nào!")

    group_msg = "**📋 Danh sách nhóm Zalo:**\n"
    for i, g in enumerate(groups, 1):
        group_msg += f"{i}. {g['name']} — `{g['id']}`\n"
    await interaction.followup.send(group_msg[:2000])
    await interaction.followup.send("👉 Nhập STT nhóm muốn spam (trong 30s)")

    def check_group(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check_group, timeout=30)
        index = int(reply.content.strip())
        if index < 1 or index > len(groups):
            raise ValueError()
    except:
        return await interaction.followup.send("⏱️ Hết thời gian hoặc STT không hợp lệ!")

    group = groups[index - 1]

    await interaction.followup.send("🎭 Chọn loại sticker:\n1. 👊 Nấm đấm\n2. 🎂 Happy Birthday\n👉 Trả lời bằng số:")

    def check_sticker(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        sticker_reply = await interaction.client.wait_for("message", check=check_sticker, timeout=30)
        choice = sticker_reply.content.strip()
        if choice == "1":
            sticker_id, cate_id = 23339, 10425
        elif choice == "2":
            sticker_id, cate_id = 21979, 10194
        else:
            raise ValueError()
    except:
        return await interaction.followup.send("❌ Lựa chọn không hợp lệ hoặc hết thời gian!")

    stop_event = threading.Event()
    thread = threading.Thread(
        target=bot.spam_sticker_loop,
        args=(group['id'], group['name'], sticker_id, cate_id, delay, stop_event),
        daemon=True
    )
    thread.start()

    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    with TREOSTICKER_LOCK:
        if discord_user_id not in user_sticker_tabs:
            user_sticker_tabs[discord_user_id] = []
        user_sticker_tabs[discord_user_id].append({
            "thread": thread,
            "stop_event": stop_event,
            "start": start_time,
            "group_name": group['name']
        })

    await interaction.followup.send(
        f"✅ Bắt đầu spam sticker vào nhóm `{group['name']}` mỗi `{delay}`s."
    )
    
@tree.command(name="tabtreosticker", description="Quản lý các sticker đang spam")
async def tabtreosticker(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)

    with TREOSTICKER_LOCK:
        tabs = user_sticker_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("❌ Không có sticker nào đang chạy!")

    tab_msg = "**📌 Các nhóm đang spam sticker:**\n"
    for i, tab in enumerate(tabs, 1):
        start_time = tab["start"].strftime("%Y-%m-%d %H:%M:%S")
        tab_msg += f"{i}. `{tab['group_name']}` — Bắt đầu: `{start_time}`\n"
    tab_msg += "\n👉 Gõ STT để dừng (trong 30s)."

    await interaction.response.send_message(tab_msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check, timeout=30)
        index = int(reply.content.strip())
        if index < 1 or index > len(tabs):
            raise ValueError()
    except:
        return await interaction.followup.send("⏱️ Hết thời gian hoặc STT không hợp lệ!")

    with TREOSTICKER_LOCK:
        stop_tab = user_sticker_tabs[discord_user_id].pop(index - 1)
        stop_tab["stop_event"].set()

    await interaction.followup.send("🛑 Đã dừng spam sticker!")  
def get_uid_fbdtsg(ck):
    try:
        headers = {
            'Accept': 'text/html',
            'Cookie': ck,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }

        response = requests.get('https://www.facebook.com/', headers=headers)
        html_content = response.text

        if '"USER_ID":"' not in html_content:
            return None, None, None, None, None, None

        user_id = re.search(r'"USER_ID":"(\d+)"', html_content)
        fb_dtsg = re.search(r'"f":"([^"]+)"', html_content)
        jazoest = re.search(r'jazoest=(\d+)', html_content)
        rev = re.search(r'"server_revision":(\d+),"client_revision":(\d+)', html_content)
        a = re.search(r'__a=(\d+)', html_content)

        user_id = user_id.group(1) if user_id else None
        fb_dtsg = fb_dtsg.group(1) if fb_dtsg else None
        jazoest = jazoest.group(1) if jazoest else None
        rev = rev.group(1) if rev else None
        a = a.group(1) if a else "1"
        req = "1b"

        if not all([user_id, fb_dtsg, jazoest, rev]):
            return None, None, None, None, None, None

        return user_id, fb_dtsg, rev, req, a, jazoest

    except Exception as e:
        print(f"Lỗi Khi Check Cookie: {e}")
        return None, None, None, None, None, None

def upload_image_get_fbid(image_path_or_url: str, ck: str) -> str:
    result = get_uid_fbdtsg(ck)
    if not result or len(result) != 6 or any(v is None for v in result):
        return "Không thể lấy thông tin từ cookie. Vui lòng kiểm tra lại."

    user_id, fb_dtsg, rev, req, a, jazoest = result

    is_url = image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://")
    try:
        if is_url:
            resp = requests.get(image_path_or_url)
            if resp.status_code != 200:
                return "Không thể tải ảnh từ URL."
            img_data = BytesIO(resp.content)
            img_data.name = "image.jpg"
        else:
            if not os.path.isfile(image_path_or_url):
                return "File không tồn tại. Hãy nhập đúng đường dẫn tới ảnh."
            img_data = open(image_path_or_url, 'rb')
    except Exception as e:
        return f"Lỗi khi đọc ảnh: {e}"

    headers = {
        'cookie': ck,
        'origin': 'https://www.facebook.com',
        'referer': 'https://www.facebook.com/',
        'user-agent': 'Mozilla/5.0',
        'x-fb-lsd': fb_dtsg,
    }

    params = {
        'av': user_id,
        'profile_id': user_id,
        'source': '19',
        'target_id': user_id,
        '__user': user_id,
        '__a': a,
        '__req': req,
        '__rev': rev,
        'fb_dtsg': fb_dtsg,
        'jazoest': jazoest,
    }

    try:
        files = {
            'file': (img_data.name, img_data, 'image/jpeg')
        }

        response = requests.post(
            'https://www.facebook.com/ajax/ufi/upload/',
            headers=headers,
            params=params,
            files=files
        )

        if is_url:
            img_data.close()

        text = response.text.strip()
        if text.startswith("for(;;);"):
            text = text[8:]

        try:
            data = json.loads(text)
            fbid = data.get("payload", {}).get("fbid")
            if fbid:
                return fbid
            return "Không tìm thấy fbid trong JSON."
        except json.JSONDecodeError:
            match = re.search(r'"fbid"\s*:\s*"(\d+)"', text)
            if match:
                return match.group(1)
            return "Không tìm thấy fbid trong text."

    except Exception as e:
        return f"Lỗi khi upload: {e}"                                                                                                              
@tree.command(name="reostr", description="Spam story ảnh + tag UID từ file nhay.txt")
@app_commands.describe(
    cookie="Cookie Facebook",
    image_link="Đường dẫn ảnh (URL hoặc local path)",
    uid_tag="UID cần tag vào ảnh",
    delay="Delay giữa mỗi lần gửi (giây)"
)
async def reostr(
    interaction: discord.Interaction,
    cookie: str,
    image_link: str,
    uid_tag: str,
    delay: float
):
    if not is_admin(interaction) and not is_authorized(interaction):
        return await safe_send(interaction, "⛔ Bạn không có quyền dùng lệnh này")

    await interaction.response.defer(thinking=True)

    info = get_uid_fbdtsg(cookie)
    if not info:
        return await interaction.followup.send("❌ Cookie không hợp lệ hoặc thiếu dữ liệu")

    user_id, fb_dtsg, rev, req, a, jazoest = info

    if not os.path.exists("nhay.txt"):
        return await interaction.followup.send("❌ Không tìm thấy file nhay.txt!")

    with open("nhay.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return await interaction.followup.send("❌ File nhay.txt không có nội dung!")

    stop_event = threading.Event()
    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    def reostr_worker():
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': cookie,
            'origin': 'https://www.facebook.com',
            'referer': 'https://www.facebook.com/stories/create',
            'user-agent': 'Mozilla/5.0',
            'x-fb-friendly-name': 'StoriesCreateMutation',
            'x-fb-lsd': fb_dtsg,
        }

        while not stop_event.is_set():
            for content_text in lines:
                if stop_event.is_set():
                    break

                # 🔁 Upload ảnh mỗi lần gửi
                fbid = upload_image_get_fbid(image_link, cookie)
                if not isinstance(fbid, str) or not fbid.isdigit():
                    print(f"❌ Lỗi upload ảnh: {fbid}")
                    continue  # bỏ qua nếu upload thất bại

                variables = {
                    "input": {
                        "audiences": [{"stories": {"self": {"target_id": user_id}}}],
                        "audiences_is_complete": True,
                        "logging": {"composer_session_id": ""},
                        "navigation_data": {"attribution_id_v2": "StoriesCreateRoot.react"},
                        "source": "WWW",
                        "message": {"ranges": [], "text": content_text},
                        "attachments": [{
                            "photo": {
                                "id": fbid,
                                "overlays": [{
                                    "tag_sticker": {
                                        "bounds": {
                                            "height": 0.0356,
                                            "rotation": 0,
                                            "width": 0.3764,
                                            "x": 0.3944,
                                            "y": 0.4582
                                        },
                                        "creation_source": "TEXT_TOOL_MENTION",
                                        "tag_id": uid_tag,
                                        "type": "PEOPLE"
                                    }
                                }]
                            }
                        }],
                        "tracking": [None],
                        "actor_id": user_id,
                        "client_mutation_id": str(time.time())
                    }
                }

                data = {
                    '__user': user_id,
                    '__a': a,
                    '__req': req,
                    'fb_dtsg': fb_dtsg,
                    'jazoest': jazoest,
                    'lsd': fb_dtsg,
                    'variables': json.dumps(variables),
                    'doc_id': '7490607150987409',
                }

                try:
                    requests.post('https://www.facebook.com/api/graphql/', headers=headers, data=data)
                    print(f"✅ Gửi story: {content_text}")
                except Exception as e:
                    print(f"❌ Lỗi gửi story: {e}")

                time.sleep(delay)

    th = threading.Thread(target=reostr_worker, daemon=True)
    th.start()

    with TAB_LOCK:
        if discord_user_id not in user_reostr_tabs:
            user_reostr_tabs[discord_user_id] = []
        user_reostr_tabs[discord_user_id].append({
            "thread": th,
            "stop_event": stop_event,
            "start": start_time,
            "fbid": None,  # không cần lưu fbid cố định nữa
            "delay": delay,
            "uid_tag": uid_tag
        })

    await interaction.followup.send(
        f"✅ Đã bắt đầu spam story ảnh tag UID `{uid_tag}` mỗi `{delay}` giây (mỗi lần upload lại ảnh)."
    )

@tree.command(name="tabreostr", description="Xem và dừng các tab story ảnh đang chạy")
async def tabreostr(interaction: discord.Interaction):
    if not is_admin(interaction) and not is_authorized(interaction):
        return await safe_send(interaction, "Bạn không có quyền dùng lệnh này")

    discord_user_id = str(interaction.user.id)
    with TAB_LOCK:
        tabs = user_reostr_tabs.get(discord_user_id, [])

    if not tabs:
        return await safe_send(interaction, "❌ Không có tab nào đang hoạt động")

    msg = "**Danh sách tab reostr của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        msg += f"{idx}. UID: `{tab['uid_tag']}` | Delay: `{tab['delay']}`s | Uptime: `{uptime}`\n"
    msg += "\n➡️ Nhập số thứ tự của tab bạn muốn **dừng**."

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏱️ Hết thời gian. Không dừng tab nào.")

    index = reply.content.strip()
    if not index.isdigit():
        return await interaction.followup.send("⚠️ Không hợp lệ.")

    i = int(index)
    if not (1 <= i <= len(tabs)):
        return await interaction.followup.send("⚠️ Số không hợp lệ.")

    with TAB_LOCK:
        chosen = tabs.pop(i - 1)
        chosen["stop_event"].set()
        if not tabs:
            del user_reostr_tabs[discord_user_id]

    await interaction.followup.send(f"⛔ Đã dừng tab reostr số `{i}`")

from toolrnboxzl import ZaloRenameBot
import threading
from datetime import datetime

@tree.command(name="nhaynameboxzl", description="Đổi tên box Zalo liên tục từ nhay.txt")
@app_commands.describe(
    imei="IMEI thiết bị Zalo",
    cookie="Cookie Zalo (JSON hoặc key=value;...)",
    delay="Delay giữa mỗi lần đổi tên (giây)"
)
async def nhaynameboxzl(interaction: discord.Interaction, imei: str, cookie: str, delay: float):
    if not is_admin(interaction) and not is_authorized(interaction):
        return await interaction.response.send_message("⛔ Bạn không có quyền dùng lệnh này.")

    await interaction.response.defer()

    # ✅ Sửa hàm parse cookie: hỗ trợ cả JSON & key=value dạng raw
    def parse_cookie_string(cookie_str):
        try:
            cookie_str = cookie_str.strip()
            if cookie_str.startswith("{") and cookie_str.endswith("}"):
                data = json.loads(cookie_str)
            else:
                data = {}
                for part in cookie_str.split(";"):
                    if "=" in part:
                        k, v = part.strip().split("=", 1)
                        data[k.strip()] = v.strip()

            # ✅ ánh xạ tự động nếu thiếu session_key
            if "session_key" not in data and "zpw_sek" in data:
                data["session_key"] = data["zpw_sek"]

            return data
        except Exception as e:
            print(f"[!] Lỗi parse cookie: {e}")
            return None

    cookies = parse_cookie_string(cookie)
    if not cookies or "session_key" not in cookies:
        return await interaction.followup.send("❌ Cookie không hợp lệ hoặc thiếu session_key.")

    bot = ZaloRenameBot(imei, cookies)
    groups = bot.fetch_groups()
    if not groups:
        return await interaction.followup.send("❌ Không tìm thấy nhóm nào!")

    msg = "**📋 Danh sách nhóm:**\n"
    for i, g in enumerate(groups, 1):
        msg += f"{i}. {g['name']} — `{g['id']}`\n"
    await interaction.followup.send(msg[:2000])
    await interaction.followup.send("👉 Nhập STT nhóm muốn đổi tên (trong 30s):")

    def check(m): return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check, timeout=30)
        index = int(reply.content.strip())
        if index < 1 or index > len(groups):
            raise ValueError()
    except:
        return await interaction.followup.send("❌ STT không hợp lệ hoặc hết thời gian.")

    group = groups[index - 1]
    stop_event = threading.Event()
    thread = threading.Thread(target=bot.rename_loop, args=(group['id'], delay, stop_event), daemon=True)
    thread.start()

    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()
    global nhaynameboxzl_tabs
    if discord_user_id not in nhaynameboxzl_tabs:
        nhaynameboxzl_tabs[discord_user_id] = []

    nhaynameboxzl_tabs[discord_user_id].append({
        "thread": thread,
        "stop_event": stop_event,
        "start": start_time,
        "group": group
    })

    await interaction.followup.send(
        f"✅ Đã bắt đầu spam đổi tên nhóm `{group['name']}` mỗi {delay}s!"
    )
    
@tree.command(name="tabnhaynameboxzl", description="Xem và dừng tab đổi tên nhóm Zalo")
async def tabnhaynameboxzl(interaction: discord.Interaction):
    if not is_admin(interaction) and not is_authorized(interaction):
        return await interaction.response.send_message("⛔ Bạn không có quyền dùng lệnh này.")

    discord_user_id = str(interaction.user.id)
    tabs = nhaynameboxzl_tabs.get(discord_user_id)
    if not tabs:
        return await interaction.response.send_message("❌ Không có tab nào đang chạy!")

    msg = "**📂 Danh sách tab đang chạy:**\n"
    for i, tab in enumerate(tabs, 1):
        uptime = datetime.now() - tab["start"]
        msg += f"{i}. Nhóm: `{tab['group']['name']}` — Uptime: `{str(uptime).split('.')[0]}`\n"
    msg += "\n👉 Nhập STT tab muốn dừng (trong 30s):"

    await interaction.response.send_message(msg[:2000])

    def check(m): return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await interaction.client.wait_for("message", check=check, timeout=30)
        index = int(reply.content.strip())
        if index < 1 or index > len(tabs):
            raise ValueError()
    except:
        return await interaction.followup.send("❌ STT không hợp lệ hoặc hết thời gian.")

    tabs[index - 1]["stop_event"].set()
    tabs.pop(index - 1)
    await interaction.followup.send("🛑 Đã dừng tab thành công!")

import discord
from discord import app_commands
import threading, os, time, re
from nenMqtt import MQTTThemeClient

# ================== QUYỀN ==================
ADMIN_IDS = ["1310263571434704988"]  # sửa thành ID admin của bạn

def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_IDS

def has_permission(interaction: discord.Interaction) -> bool:
    return is_admin(interaction.user.id)


# Lưu task cho từng user
USER_TASKS = {}  # {user_id: [ { "folder": str, "thread": Thread, "box_id": str, "delay": float } ]}


# Modal set theme
class SetThemeModal(discord.ui.Modal, title="Set Theme Messenger"):
    cookie = discord.ui.TextInput(label="Cookie Facebook", style=discord.TextStyle.paragraph, required=True)
    box_id = discord.ui.TextInput(label="ID Box/Thread", placeholder="Nhập ID nhóm chat", required=True)
    delay = discord.ui.TextInput(label="Delay (giây)", placeholder="Ví dụ: 5", default="5", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not has_permission(interaction):
            embed = discord.Embed(
                title="❌ Lỗi quyền hạn",
                description="Bạn không có quyền sử dụng lệnh này.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            cookie = str(self.cookie.value).strip()
            box_id = re.sub(r"[^\d]", "", str(self.box_id.value))
            delay = float(self.delay.value)

            if not box_id:
                embed = discord.Embed(
                    title="❌ Lỗi",
                    description="ID box không hợp lệ.",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed)

            folder_name = f"settheme_{interaction.user.id}_{int(time.time())}"
            folder_path = os.path.join("data", folder_name)
            os.makedirs(folder_path, exist_ok=True)

            # Hàm chạy set theme
            def run_set_theme():
                try:
                    client = MQTTThemeClient(cookie)
                    client.connect()
                    while os.path.exists(folder_path):
                        client.set_theme(box_id)  # random theme
                        time.sleep(delay)
                except Exception as e:
                    print(f"Lỗi set theme: {e}")
                finally:
                    try:
                        client.disconnect()
                    except:
                        pass

            t = threading.Thread(target=run_set_theme, daemon=True)
            t.start()

            # Lưu task
            if interaction.user.id not in USER_TASKS:
                USER_TASKS[interaction.user.id] = []
            USER_TASKS[interaction.user.id].append({
                "folder": folder_path,
                "thread": t,
                "box_id": box_id,
                "delay": delay
            })

            embed = discord.Embed(
                title="✅ Task Set Theme đã bắt đầu",
                description=(
                    f"**Box ID:** `{box_id}`\n"
                    f"**Delay:** `{delay}` giây\n"
                    f"**Người tạo:** {interaction.user.mention}\n\n"
                    f"⚙️ Bot sẽ set theme liên tục cho box này."
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)


# Slash command /settheme
@tree.command(name="setnenmess", description="Set theme Messenger liên tục")
async def settheme(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    embed = discord.Embed(
        title="🎨 Set Theme Messenger siêu múp",
        description="Ấn **Bắt đầu** để điền thông tin cần thiết.",
        color=discord.Color.yellow()
    )
    view = discord.ui.View()
    button = discord.ui.Button(label="Bắt đầu", style=discord.ButtonStyle.secondary)

    async def button_callback(btn_inter: discord.Interaction):
        await btn_inter.response.send_modal(SetThemeModal())

    button.callback = button_callback
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view)


# Slash command /tabsettheme
@tree.command(name="tabsetnenmess", description="Quản lý và dừng task set theme")
@app_commands.describe(stop="Nhập số task để dừng (ví dụ: 1) hoặc All để dừng tất cả")
async def tabsettheme(interaction: discord.Interaction, stop: str = None):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    user_id = interaction.user.id
    tasks = USER_TASKS.get(user_id, [])

    if not tasks:
        embed = discord.Embed(
            title="📋 Danh sách task",
            description="❌ Bạn không có task nào đang chạy.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    # Nếu user nhập số → dừng task
    if stop:
        if stop.lower() == "all":
            for task in tasks:
                if os.path.exists(task["folder"]):
                    os.rmdir(task["folder"])
            USER_TASKS[user_id] = []
            embed = discord.Embed(
                title="🛑 Dừng task",
                description="✅ Đã dừng tất cả task set theme.",
                color=discord.Color.green()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            num = int(stop) - 1
            if 0 <= num < len(tasks):
                folder = tasks[num]["folder"]
                if os.path.exists(folder):
                    os.rmdir(folder)
                tasks.pop(num)
                embed = discord.Embed(
                    title="🛑 Dừng task",
                    description=f"✅ Đã dừng task số **{stop}**.",
                    color=discord.Color.green()
                )
                return await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ Lỗi",
                    description="Số task không hợp lệ.",
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed)
        except:
            embed = discord.Embed(
                title="⚠️ Lỗi",
                description="Vui lòng nhập số hợp lệ hoặc 'all'.",
                color=discord.Color.orange()
            )
            return await interaction.response.send_message(embed=embed)

    # Nếu chưa nhập stop → hiển thị danh sách
    desc = ""
    for idx, task in enumerate(tasks, 1):
        desc += f"**{idx}.** Box `{task['box_id']}` | Delay: {task['delay']}s\n"

    embed = discord.Embed(
        title="📋 Danh sách task Set Theme",
        description=desc + "\n👉 Dùng `/tabsetnenmess stop:<số>` để dừng task.\n👉 Dùng `/tabsetnenmess stop:all` để dừng tất cả.",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)


import discord, os, threading, time, re
from discord import app_commands
from discord.ui import Button, View
from module.treopoll import start_nhay_poll_func, stop_nhay_poll

# ================== QUYỀN ==================
ADMIN_IDS = ["1310263571434704988"]  # sửa ID admin chính của bạn

def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_IDS

def has_permission(interaction: discord.Interaction) -> bool:
    return is_admin(interaction.user.id)


# Lưu task theo user
USER_POLL_TASKS = {}  # {user_id: [ { "folder": str, "thread": Thread, "box_id": str, "delay": float } ]}


# Modal nhập thông tin poll
class TreoPollModal(discord.ui.Modal, title="Treo Poll Messenger"):
    cookie = discord.ui.TextInput(label="Cookie Facebook", style=discord.TextStyle.paragraph, required=True)
    box_id = discord.ui.TextInput(label="ID Box/Thread", placeholder="Nhập ID nhóm chat", required=True)
    delay = discord.ui.TextInput(label="Delay (giây)", placeholder="Ví dụ: 30", default="30", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not has_permission(interaction):
            embed = discord.Embed(
                title="❌ Lỗi quyền hạn",
                description="Bạn không có quyền sử dụng bot.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            cookie = str(self.cookie.value).strip()
            box_id = re.sub(r"[^\d]", "", str(self.box_id.value))
            delay = float(self.delay.value)

            if not box_id:
                embed = discord.Embed(
                    title="❌ Lỗi",
                    description="ID box không hợp lệ.",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed)

            folder_name = f"treopoll_{interaction.user.id}_{int(time.time())}"
            folder_path = os.path.join("data", folder_name)
            os.makedirs(folder_path, exist_ok=True)

            # Hàm chạy treo poll
            def run_treo_poll():
                try:
                    start_nhay_poll_func(cookie, box_id, delay, folder_name)
                except Exception as e:
                    print(f"Lỗi treo poll: {e}")

            t = threading.Thread(target=run_treo_poll, daemon=True)
            t.start()

            if interaction.user.id not in USER_POLL_TASKS:
                USER_POLL_TASKS[interaction.user.id] = []
            USER_POLL_TASKS[interaction.user.id].append({
                "folder": folder_path,
                "thread": t,
                "box_id": box_id,
                "delay": delay
            })

            embed = discord.Embed(
                title="✅ Task Treo Poll đã bắt đầu",
                description=(
                    f"**Box ID:** `{box_id}`\n"
                    f"**Delay:** `{delay}` giây\n"
                    f"**Người tạo:** {interaction.user.mention}\n\n"
                    f"⚙️ Bot sẽ tạo poll liên tục trong box này."
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)


# Slash command /treopollmess
@tree.command(name="treopollmess", description="Tạo treo poll Messenger liên tục")
async def treopollmess(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng bot.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    embed = discord.Embed(
        title="📊 Treo Poll Messenger",
        description="Ấn **Start** để điền thông tin cần thiết.",
        color=discord.Color.blue()
    )
    view = View()
    button = Button(label="Start", style=discord.ButtonStyle.success)

    async def button_callback(btn_inter: discord.Interaction):
        await btn_inter.response.send_modal(TreoPollModal())

    button.callback = button_callback
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view)


# Slash command /tabtreopollmess
@tree.command(name="tabtreopollmess", description="Quản lý và dừng task treo poll")
@app_commands.describe(stop="Nhập số task để dừng (ví dụ: 1) hoặc 'all' để dừng tất cả")
async def tabtreopollmess(interaction: discord.Interaction, stop: str = None):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng bot.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    user_id = interaction.user.id
    tasks = USER_POLL_TASKS.get(user_id, [])

    if not tasks:
        embed = discord.Embed(
            title="📋 Danh sách task",
            description="❌ Bạn không có task treo poll nào đang chạy.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    # Nếu user nhập stop
    if stop:
        if stop.lower() == "all":
            for task in tasks:
                if os.path.exists(task["folder"]):
                    os.rmdir(task["folder"])
            USER_POLL_TASKS[user_id] = []
            embed = discord.Embed(
                title="🛑 Dừng task",
                description="✅ Đã dừng tất cả task treo poll.",
                color=discord.Color.green()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            num = int(stop) - 1
            if 0 <= num < len(tasks):
                folder = tasks[num]["folder"]
                if os.path.exists(folder):
                    os.rmdir(folder)
                tasks.pop(num)
                embed = discord.Embed(
                    title="🛑 Dừng task",
                    description=f"✅ Đã dừng task số **{stop}**.",
                    color=discord.Color.green()
                )
                return await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ Lỗi",
                    description="Số task không hợp lệ.",
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed)
        except:
            embed = discord.Embed(
                title="⚠️ Lỗi",
                description="Vui lòng nhập số hợp lệ hoặc 'all'.",
                color=discord.Color.orange()
            )
            return await interaction.response.send_message(embed=embed)

    # Nếu chưa nhập stop → hiển thị danh sách
    desc = ""
    for idx, task in enumerate(tasks, 1):
        desc += f"**{idx}.** Box `{task['box_id']}` | Delay: {task['delay']}s\n"

    embed = discord.Embed(
        title="📋 Danh sách task Treo Poll",
        description=desc + "\n👉 Dùng `/tabtreopollmess stop:<số>` để dừng task.\n👉 Dùng `/tabtreopollmess stop:all` để dừng tất cả.",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)
    

import discord, threading, time, re, os, shutil
from discord import app_commands
from discord.ui import Button, View

from nenMqtt import MQTTThemeClient
from toolnamebox import tenbox, dataGetHome
from module.treopoll import start_nhay_poll_func   # đảm bảo treopoll.py có hàm này

# ================== QUYỀN ==================
ADMIN_IDS = ["1310263571434704988"]  # sửa ID admin chính của bạn

def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_IDS

def has_permission(interaction: discord.Interaction) -> bool:
    return is_admin(interaction.user.id)


# Lưu task combo + stop flags
USER_COMBO_TASKS = {}   # {user_id: [ {id, task_key, box_id, delay} , ... ]}
STOP_FLAGS = {}         # { task_key: True/False }
THEME_CLIENTS = {}      # { task_key: MQTTThemeClient instance }


# ================== Hàm chạy 3 chức năng ==================
def run_theme(cookie, box_id, delay, task_key):
    print(f">>> Theme thread bắt đầu [{task_key}]")
    try:
        client = MQTTThemeClient(cookie)
        THEME_CLIENTS[task_key] = client
        client.connect()

        while not STOP_FLAGS.get(task_key, False):
            try:
                theme = client.get_random_theme()
                client.set_theme(str(box_id), theme_id=theme["id"])
                print(f"[Theme {task_key}] Đã đổi theme: {theme['name']}")
            except Exception as e:
                print(f"[Theme {task_key}] Lỗi set theme: {e}")
            time.sleep(delay)

        try:
            client.disconnect()
        except:
            pass
        print(f">>> Theme thread stopped [{task_key}]")
    except Exception as e:
        print(f"[Theme {task_key}] Lỗi theme: {e}")


def run_poll(cookie, box_id, delay, user_id, task_key):
    folder_name = f"combopoll_{task_key}"
    folder_path = os.path.join("data", folder_name)
    print(f">>> Poll thread bắt đầu [{task_key}] -> folder: {folder_path}")
    try:
        os.makedirs(folder_path, exist_ok=True)
        start_nhay_poll_func(cookie, box_id, delay, folder_name)
    except Exception as e:
        print(f"[Poll {task_key}] Lỗi poll: {e}")
    finally:
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                print(f"[Poll {task_key}] Dọn xong folder {folder_path}")
        except Exception as e:
            print(f"[Poll {task_key}] Lỗi dọn folder: {e}")
    print(f">>> Poll thread stopped [{task_key}]")


def run_namebox(cookie, box_id, delay, task_key):
    print(f">>> NameBox thread bắt đầu [{task_key}]")
    try:
        dataFB = dataGetHome(cookie)
        if not dataFB:
            print(f"[NameBox {task_key}] ❌ Lỗi: dataGetHome trả về None, dừng NameBox.")
            return

        nhay_file = "nhay.txt"
        if not os.path.exists(nhay_file):
            with open(nhay_file, "w", encoding="utf-8") as f:
                f.write("TestName\n")
            print(f"[NameBox {task_key}] ⚠️ Không tìm thấy nhay.txt, đã tạo file mặc định.")

        while not STOP_FLAGS.get(task_key, False):
            try:
                with open(nhay_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"[NameBox {task_key}] Lỗi đọc nhay.txt: {e}")
                break

            if not lines:
                print(f"[NameBox {task_key}] nhay.txt rỗng, chờ {delay}s rồi thử lại.")
                time.sleep(delay)
                continue

            for name in lines:
                if STOP_FLAGS.get(task_key, False):
                    break
                try:
                    success, log = tenbox(name, box_id, dataFB)
                    print(f"[NameBox {task_key}] {log}")
                except Exception as e:
                    print(f"[NameBox {task_key}] ❌ Lỗi tenbox với '{name}': {e}")
                time.sleep(delay)

        print(f">>> NameBox thread stopped [{task_key}]")
    except Exception as e:
        print(f"[NameBox {task_key}] Lỗi namebox tổng: {e}")


def run_combo(cookie, box_id, delay, user_id, task_key):
    STOP_FLAGS[task_key] = False
    threading.Thread(target=run_theme, args=(cookie, box_id, delay, task_key), daemon=True).start()
    threading.Thread(target=run_poll, args=(cookie, box_id, delay, user_id, task_key), daemon=True).start()
    threading.Thread(target=run_namebox, args=(cookie, box_id, delay, task_key), daemon=True).start()


# ================== Modal nhập thông tin ==================
class ComboMessModal(discord.ui.Modal, title="ComboMess"):
    cookie = discord.ui.TextInput(label="Cookie Facebook", style=discord.TextStyle.paragraph, required=True)
    box_id = discord.ui.TextInput(label="ID Box/Thread", placeholder="Nhập ID nhóm chat", required=True)
    delay = discord.ui.TextInput(label="Delay (giây)", placeholder="Ví dụ: 30", default="30", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not has_permission(interaction):
            embed = discord.Embed(
                title="❌ Lỗi quyền hạn",
                description="Bạn không có quyền sử dụng bot.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            cookie = str(self.cookie.value).strip()
            box_id = re.sub(r"[^\d]", "", str(self.box_id.value))
            delay = float(self.delay.value)

            if not box_id:
                embed = discord.Embed(
                    title="❌ Lỗi",
                    description="ID box không hợp lệ.",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed)

            if interaction.user.id not in USER_COMBO_TASKS:
                USER_COMBO_TASKS[interaction.user.id] = []
            task_id = len(USER_COMBO_TASKS[interaction.user.id]) + 1
            task_key = f"{interaction.user.id}_{task_id}"

            t = threading.Thread(target=run_combo, args=(cookie, box_id, delay, interaction.user.id, task_key), daemon=True)
            t.start()

            USER_COMBO_TASKS[interaction.user.id].append({
                "id": task_id,
                "task_key": task_key,
                "box_id": box_id,
                "delay": delay
            })

            embed = discord.Embed(
                title="🚀 ComboMess đã khởi động",
                description=(
                    f"**Box ID:** `{box_id}`\n"
                    f"**Delay:** `{delay}` giây\n"
                    f"**Task ID:** `{task_id}`\n"
                    f"**Người tạo:** {interaction.user.mention}\n\n"
                    "⚙️ Bot đang chạy 3 chức năng: Theme, Poll, NameBox."
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Lỗi",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)


# ================== Slash command /combomess ==================
@tree.command(name="combomess", description="Chạy combo Theme + Poll + NameBox cùng lúc")
async def combomess(interaction: discord.Interaction):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng bot.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    embed = discord.Embed(
        title="🔱 ComboMess",
        description="Ấn **Start** để điền cookie, id box và delay.",
        color=discord.Color.blue()
    )
    view = View()
    button = Button(label="Start", style=discord.ButtonStyle.secondary)

    async def button_callback(btn_inter: discord.Interaction):
        await btn_inter.response.send_modal(ComboMessModal())

    button.callback = button_callback
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view)


# ================== Slash command /tabcombomess ==================
@tree.command(name="tabcombomess", description="Quản lý và dừng combo task")
@app_commands.describe(stop="Nhập số task để dừng (ví dụ: 1) hoặc 'all' để dừng tất cả")
async def tabcombomess(interaction: discord.Interaction, stop: str = None):
    if not has_permission(interaction):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng bot.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    user_id = interaction.user.id
    tasks = USER_COMBO_TASKS.get(user_id, [])

    if not tasks:
        embed = discord.Embed(
            title="📋 Danh sách task",
            description="❌ Bạn không có task ComboMess nào đang chạy.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    if stop:
        if stop.lower() == "all":
            for task in list(tasks):
                STOP_FLAGS[task["task_key"]] = True
                if task["task_key"] in THEME_CLIENTS:
                    try:
                        THEME_CLIENTS[task["task_key"]].disconnect()
                    except:
                        pass
                    try:
                        del THEME_CLIENTS[task["task_key"]]
                    except:
                        pass
                folder_path = os.path.join("data", f"combopoll_{task['task_key']}")
                try:
                    if os.path.exists(folder_path):
                        shutil.rmtree(folder_path)
                        print(f"[Stop] Xóa folder poll {folder_path}")
                except Exception as e:
                    print(f"[Stop] Lỗi xóa folder {folder_path}: {e}")
            USER_COMBO_TASKS[user_id] = []
            embed = discord.Embed(
                title="🛑 Dừng task",
                description="✅ Đã dừng tất cả task ComboMess.",
                color=discord.Color.green()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            num = int(stop) - 1
            if 0 <= num < len(tasks):
                task = tasks.pop(num)
                STOP_FLAGS[task["task_key"]] = True

                if task["task_key"] in THEME_CLIENTS:
                    try:
                        THEME_CLIENTS[task["task_key"]].disconnect()
                    except:
                        pass
                    try:
                        del THEME_CLIENTS[task["task_key"]]
                    except:
                        pass

                folder_path = os.path.join("data", f"combopoll_{task['task_key']}")
                try:
                    if os.path.exists(folder_path):
                        shutil.rmtree(folder_path)
                        print(f"[Stop] Xóa folder poll {folder_path}")
                except Exception as e:
                    print(f"[Stop] Lỗi xóa folder {folder_path}: {e}")

                embed = discord.Embed(
                    title="🛑 Dừng task",
                    description=f"✅ Đã dừng task số **{stop}**.",
                    color=discord.Color.green()
                )
                return await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ Lỗi",
                    description="Số task không hợp lệ.",
                    color=discord.Color.orange()
                )
                return await interaction.response.send_message(embed=embed)
        except:
            embed = discord.Embed(
                title="⚠️ Lỗi",
                description="Vui lòng nhập số hợp lệ hoặc 'all'.",
                color=discord.Color.orange()
            )
            return await interaction.response.send_message(embed=embed)

    desc = ""
    for idx, task in enumerate(tasks, 1):
        desc += f"**{idx}.** Box `{task['box_id']}` | Delay: {task['delay']}s | Key: `{task['task_key']}`\n"

    embed = discord.Embed(
        title="📋 Danh sách task ComboMess",
        description=desc + "\n👉 Dùng `/tabcombomess stop:<số>` để dừng task.\n👉 Dùng `/tabcombomess stop:all` để dừng tất cả.",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)





import discord
from discord import app_commands

user_task_logs = []  
ADMIN_IDS = ["123456789012345678"]  # đổi sang ID admin của bạn

IGNORED_COMMANDS = {
    "listadmin",
    "addadmin",
    "xoaadmin",
    "menu",
    "checkuid",
    "idkenh",
    "checktask"
}

def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_IDS


@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    if command.name in IGNORED_COMMANDS:
        return

    user_task_logs.append({
        "user_id": str(interaction.user.id),
        "command": command.name,
        "start": datetime.now()
    })


@tree.command(name="checktask", description="Xem các task spam đang chạy (Admin only)")
async def checktask(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền dùng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    embed = discord.Embed(
        title="📊 Danh sách task spam đang chạy",
        color=discord.Color.blurple(),
        timestamp=datetime.datetime.now()
    )

    if not user_task_logs:
        embed.add_field(
            name="Trạng thái",
            value="📭 Hiện chưa có task nào đang chạy.",
            inline=False
        )
    else:
        now = datetime.datetime.now()
        for log in user_task_logs[-20:]:
            user = f"<@{log['user_id']}>"
            cmd = log["command"]
            start = log["start"]
            runtime = now - start
            h, rem = divmod(int(runtime.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

            embed.add_field(
                name=f"👤 {user}",
                value=(
                    f"🔧 Lệnh: `{cmd}`\n"
                    f"📅 Bắt đầu: {start.strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"⏱️ Đã chạy: {uptime_str}"
                ),
                inline=False
            )

    await interaction.response.send_message(embed=embed)

    
    
from discord import app_commands
import discord
from datetime import datetime

ADMIN_IDS = ["1310263571434704988"]  # thay bằng ID admin chính của bạn
user_admins = set()  # có thể thêm admin phụ vào đây

def is_admin(user_id: int) -> bool:
    """Kiểm tra quyền admin chính hoặc admin phụ"""
    return str(user_id) in ADMIN_IDS or str(user_id) in user_admins


@tree.command(
    name="checkuid",
    description="Xem thông tin chi tiết của một user qua UID Discord (Admin hoặc Admin phụ)"
)
@app_commands.describe(uid="Nhập UID Discord của người cần tra")
async def checkuid(interaction: discord.Interaction, uid: str):
    # ✅ Check quyền
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền dùng lệnh này.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        return await interaction.response.send_message(embed=embed)

    # ✅ Tìm user qua UID
    try:
        user_id = int(uid)
        user = await bot.fetch_user(user_id)
    except Exception:
        embed = discord.Embed(
            title="❌ Không tìm thấy user",
            description=f"Không tìm thấy user với UID `{uid}`.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        return await interaction.response.send_message(embed=embed)

    # ✅ Embed thông tin chi tiết
    embed = discord.Embed(
        title="🔍 Thông tin người dùng được tra cứu",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
    embed.add_field(name="👤 User", value=f"<@{user.id}>", inline=True)
    embed.add_field(name="🆔 UID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="💬 Username", value=f"`{user.name}`", inline=True)

    if user.global_name:
        embed.add_field(name="🌍 Global Name", value=f"`{user.global_name}`", inline=True)

    if hasattr(user, "pronouns") and user.pronouns:
        embed.add_field(name="🙋 Pronouns", value=f"`{user.pronouns}`", inline=True)

    embed.add_field(
        name="📅 Ngày tạo tài khoản",
        value=f"`{user.created_at.strftime('%d/%m/%Y %H:%M:%S')}`",
        inline=False
    )

    await interaction.response.send_message(embed=embed)




@tree.command(name="idkenh", description="Lấy ID kênh hiện tại")
async def idkenh(interaction: discord.Interaction):
    # ✅ Check quyền
    if str(interaction.user.id) not in ADMIN_IDS:
        embed = discord.Embed(
            title="❌ Lỗi quyền hạn",
            description="Bạn không có quyền sử dụng lệnh này.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    channel = interaction.channel
    if channel is None:
        embed = discord.Embed(
            title="❌ Lỗi",
            description="Không thể lấy kênh hiện tại.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    channel_id = channel.id

    # Phân biệt server channel và DM
    if isinstance(channel, discord.DMChannel):
        channel_display = f"Tin nhắn trực tiếp với {channel.recipient}"
        guild_name = "Không thuộc server (DM)"
    else:
        channel_display = channel.mention
        guild_name = interaction.guild.name if interaction.guild else "Không rõ server"

    # Embed chính
    main_embed = discord.Embed(
        title="📋 Channel Info",
        description=f"Thông tin kênh trong **{guild_name}**",
        color=0x5865F2
    )
    main_embed.add_field(name="Tên kênh", value=channel_display, inline=False)
    main_embed.set_footer(text="Bấm nút bên dưới để hiện ID kênh")

    # View chứa nút
    class CopyView(discord.ui.View):
        def __init__(self, cid: int):
            super().__init__(timeout=None)
            self.cid = cid

        @discord.ui.button(label="📋 Hiện Channel ID", style=discord.ButtonStyle.primary, emoji="🔑")
        async def copy_btn(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            copy_embed = discord.Embed(
                title="📋 Channel ID",
                description=f"```{self.cid}```",
                color=0x57F287
            )
            copy_embed.set_footer(text="Ai cũng có thể thấy ID này")
            await interaction_btn.response.send_message(embed=copy_embed)

    view = CopyView(channel_id)

    # Gửi embed + view
    await interaction.response.send_message(embed=main_embed, view=view)

from discord import app_commands
import discord, asyncio

# Giới hạn số kênh tối đa
MAX_CREATE = 50
DEFAULT_COUNT = 2
DEFAULT_DELAY = 5

# Danh sách admin chính
ADMIN_IDS = {"1310263571434704988"}  # thay bằng UID admin thật
# Danh sách admin phụ (có thể thêm qua lệnh khác)
user_admins = set()

def has_permission(interaction: discord.Interaction) -> bool:
    """Check nếu user là admin chính hoặc admin phụ"""
    return str(interaction.user.id) in ADMIN_IDS or str(interaction.user.id) in user_admins


import discord, asyncio
from discord import app_commands

# Giới hạn mặc định
DEFAULT_COUNT = 2
DEFAULT_DELAY = 5
MAX_CREATE = 50

# Lưu danh sách kênh bot đã tạo {guild_id: [channel_id, ...]}
RAID_CHANNELS = {}

# Hàm check quyền
def has_permission(interaction: discord.Interaction) -> bool:
    ADMIN_IDS = ["1310263571434704988"]  # sửa theo admin thật
    return str(interaction.user.id) in ADMIN_IDS


# Modal nhập thông tin tạo kênh
class RaidChannelModal(discord.ui.Modal, title="🚀 Tạo nhiều kênh trong server"):
    guild_id = discord.ui.TextInput(label="Guild ID (Server)", required=True, placeholder="Nhập ID server")
    count = discord.ui.TextInput(label="Số lượng kênh", required=False, default=str(DEFAULT_COUNT))
    delay = discord.ui.TextInput(label="Delay (giây)", required=False, default=str(DEFAULT_DELAY))
    base_name = discord.ui.TextInput(label="Tên gốc kênh", required=False, default="channel")

    async def on_submit(self, interaction: discord.Interaction):
        if not has_permission(interaction):
            embed = discord.Embed(
                title="🚫 Không có quyền",
                description="Bạn không có quyền dùng lệnh này.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed)

        try:
            guild_id = int(str(self.guild_id))
            count = int(str(self.count)) if self.count else DEFAULT_COUNT
            delay = float(str(self.delay)) if self.delay else DEFAULT_DELAY
            base_name = str(self.base_name) if self.base_name else "channel"
        except Exception:
            return await interaction.response.send_message(
                embed=discord.Embed(title="❌ Lỗi", description="Thông tin nhập không hợp lệ!", color=discord.Color.red())
            )

        guild = interaction.client.get_guild(guild_id)
        if not guild:
            return await interaction.response.send_message(
                embed=discord.Embed(title="❌ Lỗi", description="Không tìm thấy server hoặc bot chưa tham gia.", color=discord.Color.red())
            )

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=discord.Embed(title="❌ Lỗi quyền", description="Bot không có quyền **Manage Channels**.", color=discord.Color.red())
            )

        if count > MAX_CREATE:
            return await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Quá giới hạn", description=f"Tối đa {MAX_CREATE} kênh!", color=discord.Color.orange())
            )

        # Thông báo bắt đầu
        start_embed = discord.Embed(
            title="⚡ Đang tạo kênh",
            description=f"Tạo `{count}` kênh trong **{guild.name}**.\nDelay: `{delay}` giây",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=start_embed)

        created = []
        for i in range(count):
            try:
                ch = await guild.create_text_channel(f"{base_name}-{i+1}")
                created.append(ch)
                await asyncio.sleep(delay)
            except Exception as e:
                print("Lỗi tạo kênh:", e)

        RAID_CHANNELS[guild.id] = [c.id for c in created]

        result = discord.Embed(
            title="✅ Hoàn tất",
            description=f"Đã tạo **{len(created)}** kênh trong server **{guild.name}**.",
            color=discord.Color.green()
        )
        if created:
            preview = "\n".join([f"📌 {ch.mention}" for ch in created[:10]])
            if len(created) > 10:
                preview += f"\n... và {len(created)-10} kênh khác."
            result.add_field(name="Danh sách kênh", value=preview, inline=False)

        await interaction.followup.send(embed=result)


# View với 2 nút
class RaidChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 Tạo kênh", style=discord.ButtonStyle.green)
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RaidChannelModal())

    @discord.ui.button(label="🗑️ Xóa kênh đã tạo", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_permission(interaction):
            return await interaction.response.send_message(
                embed=discord.Embed(title="🚫 Không có quyền", description="Bạn không thể xóa kênh.", color=discord.Color.red())
            )

        guild = interaction.guild
        if not guild or guild.id not in RAID_CHANNELS:
            return await interaction.response.send_message(
                embed=discord.Embed(title="ℹ️ Không có kênh", description="Không có kênh nào để xóa.", color=discord.Color.orange())
            )

        channels_to_delete = RAID_CHANNELS[guild.id]
        deleted = 0
        for cid in channels_to_delete:
            ch = guild.get_channel(cid)
            if ch:
                try:
                    await ch.delete()
                    deleted += 1
                except:
                    pass

        RAID_CHANNELS.pop(guild.id, None)

        embed = discord.Embed(
            title="🗑️ Đã xóa kênh",
            description=f"Đã xóa **{deleted}** kênh trong **{guild.name}**.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)


# Slash command chính
@tree.command(name="raidtaokenh", description="Quản lý tạo kênh hàng loạt (Admin only)")
async def raidtaokenh(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚡ Raid Server - Quản lý kênh",
        description="Dùng nút bên dưới để **tạo kênh** hoặc **xóa kênh đã tạo**.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=RaidChannelView())



admin_id = 1310263571434704988
    
# ================== DROPDOWN MENU ==================
class MenuSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Quản lí", value="Quản lí", description="All lệnh chính", emoji="🛠️"),
            discord.SelectOption(label="Messenger", value="messenger", description="Các lệnh spam/dừng trên Messenger", emoji="💬"),
            discord.SelectOption(label="Facebook", value="facebook", description="Các lệnh spam/dừng trên Facebook", emoji="📘"),
            discord.SelectOption(label="Discord", value="discord", description="Các lệnh spam/dừng trên Discord", emoji="🎮"),
            discord.SelectOption(label="Zalo", value="zalo", description="Các lệnh spam/dừng trên Zalo", emoji="📞"),
            discord.SelectOption(label="Telegram", value="telegram", description="Các lệnh spam/dừng trên Telegram", emoji="📢"),
            discord.SelectOption(label="Gmail", value="gmail", description="Các lệnh spam/dừng trên Gmail", emoji="✉"),
            discord.SelectOption(label="SMS", value="sms", description="Các lệnh spam/dừng SMS", emoji="📲"),
            discord.SelectOption(label="Wechat", value="wechat", description="Các lệnh spam/dừng Wechat", emoji="💼"),
            discord.SelectOption(label="Instagram", value="instagram", description="Các lệnh spam/dừng IG", emoji="📷"),
        ]
        super().__init__(placeholder="⬇️ Chọn danh mục để xem lệnh của bot...", 
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "messenger":
            embed = discord.Embed(
                title="📱 Messenger",
                description="`/treoanhmess` - treo ảnh mess\n `/treomess` - treo 1 ndung mess\n `/nhaymess` - nhây mess\n `/nhaytagmess` - nhây đa tag mess\n `/nhaynamebox` - nhây name box\n `/tabnhaymess` - tab dừng nhây mess\n `/tabnhaytagmess` - tab dừng nhây tag mess\n `/tabnhaynamebox` - tab dừng nhây name box\n `setnenmess` - set nền mess liên tục\n `tabsetnenmess` - dừng tab set nền mess\n `treopollmess` - treo poll mess bất tử\n `tabtreopollmess` - tab treo poll mess\n `/combomess` - tạo 1 combo mess treo cực bá",
                color=discord.Color.pink()
            )

        elif self.values[0] == "facebook":
            embed = discord.Embed(
                title="📘 Facebook",
                description="`/nhaytop` - nhây bài viết\n `/anhtop` - treo ảnh bài viết\n `/tabnhaytop` - dừng tab nhây bài top\n `/tabanhtop` - dừng tap nhây ảnh top",
                color=discord.Color.pink()
            )

        elif self.values[0] == "discord":
            embed = discord.Embed(
                title="🎮 Discord",
                description="`/alltreodis` - all các lệnh treo discord\n `/allnhaydis` - all lệnh nhây dis\n `/taballtreodis` - dừng tab treo discord\n `/taballnhaydis` - dừng all tab nhây discord\n `raidtaokenh` - tạo kênh sever discord nhanh bằng bot",
                color=discord.Color.purple()
            )

        elif self.values[0] == "telegram":
            embed = discord.Embed(
                title="📢 Telegram",
                description="`/treotele` - treo ngôn telegram\n, `/tabtreotele` - dừng tab telegram",
                color=discord.Color.red()
            )

        elif self.values[0] == "zalo":
            embed = discord.Embed(
                title="📞 Zalo",
                description="`/treozalo` - treo zalo\n `/nhaytagzalo` - nhây tag zalo\n `/treopollzl` - treo bình chọn zalo\n `/nhaynameboxzl` - nhây name box zalo\n `/treosticker` - treo sờ tích cơ zalo\n `/tabtreozalo` - dừng tab treo zalo\n `/tabnhaynameboxzl` - dừng tab nhây name box zalo\n `/tabtreosticker` - dừng tab treo sticker zalo",
                color=discord.Color.green()
            )

        elif self.values[0] == "gmail":
            embed = discord.Embed(
                title="✉ Gmail",
                description="`/treogmail` - treo gmail\n `/tabtreogmail` - dừng treo gmail",
                color=discord.Color.red()
            )

        elif self.values[0] == "sms":
            embed = discord.Embed(
                title="📱 SMS",
                description="`/treosms` - treo sms\n `/tabtreosms` - dừng treo sms",
                color=discord.Color.orange()
            )

        elif self.values[0] == "wechat":
            embed = discord.Embed(
                title="💼 Wechat",
                description="`/treowechat` - treo wechat\n `/tabtreowechat` - dừng treo wechat",
                color=discord.Color.orange()
            )

        elif self.values[0] == "instagram":
            embed = discord.Embed(
                title="📷 Instagram",
                description="`/treoig` - treo ig\n `/tabtreoig` - dừng treo ig",
                color=discord.Color.magenta()
            )
        
        elif self.values[0] == "Quản lí":
            embed = discord.Embed(
                title="🛠️ Quản lí",
                description="`/menu` - hiển thị menu bot\n `/checkcookie` - check cookie fb\n`/checkuid` - check uid discord\n`/checktask` - check task đang chạy\n `/idkenh` - lấy id kênh discord",
                color=discord.Color.blue()
            )

        else:
            embed = discord.Embed(
                title="❌ Không có lệnh", 
                description="Chọn sai danh mục!", 
                color=discord.Color.blue()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class MenuDropdown(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuSelect())

# MENU CHÍNH BY MẠNH BÙI
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

        
        self.add_item(discord.ui.Button(
            label="🌐 Cre: Mbui", 
            style=discord.ButtonStyle.link, 
            url="https://guns.lol/manhbui"  
        ))

    @discord.ui.button(label="👋 chào", style=discord.ButtonStyle.success)
    async def msg_btn2(self, interaction: discord.Interaction, button: Button):
        info_embed = discord.Embed(
            title="⚙️Pro Bot 9app V5",
            description=(
                "- 👋 Xin chào bạn nhé!, tớ là pro9 viết tắt của pro bot 9app\n"
                "- cảm ơn bạn đã tin tưởng và sử dụng mình😆\n"
                f"- 🤖 người tạo ra tớ là <@{admin_id}>"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=info_embed)
        
    @discord.ui.button(label="📘 Hướng dẫn", style=discord.ButtonStyle.primary)
    async def help_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="📖 Hướng dẫn cách lệnh sử dụng bot",
            description="⬇️ Chọn danh mục bên dưới để xem các lệnh chi tiết.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=MenuDropdown())

    @discord.ui.button(label="📊 Thông tin bot", style=discord.ButtonStyle.success)
    async def info_btn(self, interaction: discord.Interaction, button: Button):
        info_embed = discord.Embed(
            title="🤖 Thông tin Bot",
            description=(
                "👤 Tác giả: **Mạnh Bùi**\n"
                "⚙️ Version: 1.2.0\n"
                "💻 Ngôn ngữ: Python + discord.py\n"
                "📅 Ngày ra mắt: 31/8/2025\n"
                f"- Cần hỗ trợ ib: <@{admin_id}>"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=info_embed)

# ================== LỆNH /MENU ==================
@bot.tree.command(name="menu", description="Hiển thị danh sách chức năng của bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title=" ⚙️  ・🄼🄴🄽🅄 🄱🄾🅃",
        description=" - 9app pro bot by sever Bach Thien Gioi",
        color=discord.Color.purple()
    )

    embed.set_thumbnail(url="https://scontent.fhph1-3.fna.fbcdn.net/v/t1.15752-9/380111370_632352538795031_2022401408807633716_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=9f807c&_nc_eui2=AeHNxkZiA8zvY1UpllzpxlAgu3h_t9gDEJW7eH-32AMQlf_Vs7Cq-jGaz_lKBXwt1LFxagUNXOZzIxEqQcE6xNQj&_nc_ohc=bMzSiIfH8uEQ7kNvwGkmTcU&_nc_oc=AdmbvkuMCag9nMkI4GOm74MDoUKYAnsUDR0EOKZ1leTpJ5IyQBXYaZnTvl7GDeZjmhZuQKAqw6dkuRf69rB7wWRu&_nc_zt=23&_nc_ht=scontent.fhph1-3.fna&oh=03_Q7cD3gGvAGXb6IA7lNH9TPKPOlVCbiSKEyGDOCQEY0yul3Fchw&oe=69059C17")
    embed.set_image(url="https://media.discordapp.net/attachments/1402549122803961856/1423235320173957120/togif.gif?ex=68df92ae&is=68de412e&hm=283c3dde5729a78202580a4a046cc9b50126a7e49afa234754d0e9d2e2bc382a&=")
    embed.set_footer(text="👉 Chúc bạn sàn war vui vẻ 🔥.\n🛠 Bot war by Mạnh Bùi")

    await interaction.response.send_message(embed=embed, view=MenuView())


bot.run(TOKEN)

COLORS = {'vang': ''}  # TODO: define actual colors