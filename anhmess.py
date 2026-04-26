import requests
import json
import time
import random
import re
import glob
import os
from pystyle import Colors, Colorate
import sys
from time import sleep
import httpx
import ssl
import certifi
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import requests
from time import sleep
from urllib.parse import urlparse

import os
import re
import sys
import time
import json
import requests
from time import sleep
from urllib.parse import urlparse

class NanhMessenger:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = self.id_user()
        self.fb_dtsg = None
        self.jazoest = None
        self.init_params()

    def id_user(self):
        try:
            return re.search(r"c_user=(\d+)", self.cookie).group(1)
        except:
            raise Exception("Cookie không hợp lệ")

    def init_params(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0',
        }
        try:
            response = requests.get('https://www.facebook.com', headers=headers)
            fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
            jazoest_match = re.search(r'name="jazoest" value="(\d+)"', response.text)

            if not fb_dtsg_match:
                response = requests.get('https://mbasic.facebook.com', headers=headers)
                fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
                jazoest_match = re.search(r'name="jazoest" value="(\d+)"', response.text)

            if fb_dtsg_match:
                self.fb_dtsg = fb_dtsg_match.group(1)
                self.jazoest = jazoest_match.group(1) if jazoest_match else "22036"
            else:
                raise Exception("Không thể lấy được fb_dtsg")
        except Exception as e:
            raise Exception(f"Lỗi khi khởi tạo tham số: {str(e)}")

    def up(self, image_url):
        try:
            filename = os.path.basename(urlparse(image_url).path) or "temp.jpg"
            r = requests.get(image_url)
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(r.content)
            else:
                return None
        except Exception:
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/',
        }

        params = {
            '__user': self.user_id,
            'fb_dtsg': self.fb_dtsg,
            '__a': '1',
            '__req': 'z',
            '__comet_req': '15'
        }

        cookies = {k.strip(): v for k, v in (x.split('=') for x in self.cookie.split(';') if '=' in x)}

        files = {
            'upload_1024': (filename, open(filename, 'rb'), 'image/jpeg'),
        }

        print("[📤] Đang upload ảnh lên Messenger...")
        try:
            res = requests.post(
                'https://www.facebook.com/ajax/mercury/upload.php',
                headers=headers,
                params=params,
                cookies=cookies,
                files=files
            )
            if res.status_code == 200:
                json_text = res.text.replace('for (;;);', '')
                data = json.loads(json_text)
                metadata = data.get('payload', {}).get('metadata', {})
                for key in metadata:
                    image_id = metadata[key].get('image_id')
                    if image_id:
                        print(f"[✓] Upload ảnh thành công - ID: {image_id}")
                        return image_id
                print("[❌] Không tìm thấy image_id.")
                return None
            else:
                return None
        except Exception:
            return None
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def gui_tn(self, recipient_id, message, image_id=None):
        self.init_params()
        timestamp = int(time.time() * 1000)
        offline_threading_id = str(timestamp)
        message_id = str(timestamp)

        data = {
            'thread_fbid': recipient_id,
            'action_type': 'ma-type:user-generated-message',
            'body': message,
            'client': 'mercury',
            'author': f'fbid:{self.user_id}',
            'timestamp': timestamp,
            'source': 'source:chat:web',
            'offline_threading_id': offline_threading_id,
            'message_id': message_id,
            'ephemeral_ttl_mode': '',
            '__user': self.user_id,
            '__a': '1',
            '__req': '1b',
            '__rev': '1015919737',
            'fb_dtsg': self.fb_dtsg,
            'jazoest': self.jazoest
        }

        if image_id:
            data['has_attachment'] = 'true'
            data['image_ids'] = [image_id]

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Referer': f'https://www.facebook.com/messages/t/{recipient_id}'
        }

        cookies = {k.strip(): v for k, v in (x.split('=') for x in self.cookie.split(';') if '=' in x)}

        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, cookies=cookies)
            if response.status_code != 200:
                print(f"[❌] Gửi tin nhắn thất bại. Status: {response.status_code}")
                return {'success': False}

            if 'for (;;);' in response.text:
                json_data = json.loads(response.text.replace('for (;;);', ''))
                if 'error' in json_data:
                    err_msg = json_data.get('errorDescription', 'Unknown error')
                    print(f"[❌] Lỗi từ phía Facebook: {err_msg}")
                    return {'success': False, 'error_description': err_msg}

            print("[✅] Gửi tin nhắn thành công.")
            return {'success': True}
        except Exception as e:
            print(f"[❌] Lỗi khi gửi tin nhắn: {e}")
            return {'success': False}
        
if __name__ == "__main__":
    try:
        cookie = input("[+] Nhập cookie Facebook:\n> ").strip()
        messenger = NanhMessenger(cookie)
        print(f"[✓] Đã xác thực cookie - user_id: {messenger.user_id}")

        recipient_id = input("[+] Nhập ID box: ").strip()
        image_link = input("[+] Nhập LINK ảnh (jpg/png): ").strip()
        file_txt = input("[+] Nhập đường dẫn file .txt chứa nội dung: ").strip()
        delay = float(input("[+] Nhập delay (s): ").strip())

        if not os.path.isfile(file_txt):
            print(f"[!] File không tồn tại: {file_txt}")
            exit()

        print("\n[*] Bắt đầu gửi tin nhắn...\n")

        while True:
            try:
                with open(file_txt, 'r', encoding='utf-8') as f:
                    message = f.read().strip()

                if not message:
                    print("[!] Nội dung rỗng.")
                    break

                image_id = messenger.up(image_link)
                if not image_id:
                    print("[!] Không thể upload ảnh. Bỏ qua lần gửi này.")
                    continue

                result = messenger.gui_tn(recipient_id, message, image_id)

                if result.get('success'):
                    print(f"[✓] Gửi thành công nội dung từ {file_txt}")
                elif "Túto akciu nemôžete vykonať" in result.get("error_description", ""):
                    print("[🚫] Facebook chặn hành động gửi. Bỏ qua tin nhắn này.")
                else:
                    print(f"[×] Gửi thất bại từ {file_txt}.")

            except Exception as e:
                print(f"[!] Lỗi xử lý file: {str(e)}")

            sys.stdout.write("[*] Đang chờ ")
            for _ in range(int(delay)):
                sys.stdout.write("⌛")
                sys.stdout.flush()
                sleep(1)
            sys.stdout.write("\n")

    except Exception as e:
        print(f"[!] Lỗi tổng: {str(e)}")