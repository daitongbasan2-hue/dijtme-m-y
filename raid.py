# fb.py
import json
import time
import random
import re
import string
from os.path import basename
from mimetypes import guess_type
import attr
import json
import random
from os.path import basename
from mimetypes import guess_type 
import requests

def Headers(setCookies, dataForm=None, Host=None):
     if (Host == None): Host = "www.facebook.com"
     headers = {}
     headers["Host"] = Host
     headers["Connection"] = "keep-alive"
     if (dataForm != None):
          headers["Content-Length"] = str(len(dataForm))
     headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
     headers["Accept"] = "*/*"
     headers["Origin"] = "https://" + Host
     headers["Sec-Fetch-Site"] = "same-origin"
     headers["Sec-Fetch-Mode"] = "cors"
     headers["Sec-Fetch-Dest"] = "empty"
     headers["Referer"] = "https://" + Host
     headers["Accept-Language"] = "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
     
     return headers
     
def digitToChar(digit):
     if digit < 10:
          return str(digit)
     return chr(ord("a") + digit - 10)

def str_base(number, base):
     if number < 0:
          return "-" + str_base(-number, base)
     (d, m) = divmod(number, base)
     if d > 0:
          return str_base(d, base) + digitToChar(m)
     return digitToChar(m)

def parse_cookie_string(cookie_string):
     cookie_dict = {}
     cookies = cookie_string.split(";")

     for cookie in cookies:
          if "=" in cookie:
               key, value = cookie.split("=")
               key = key.strip()
               value = value.strip()
               cookie_dict[key] = value
     return cookie_dict

def dataSplit(string1, string2, numberSplit1=None, numberSplit2=None, HTML=None, amount=None, string3=None, numberSplit3=None, defaultValue=None):
     if (defaultValue): numberSplit1, numberSplit2 = 1, 0
     if (amount == None):
          return HTML.split(string1)[numberSplit1].split(string2)[numberSplit2]
     elif (amount == 3):
          return HTML.split(string1)[numberSplit1].split(string2)[numberSplit2].split(string3)[numberSplit3]
     
def formAll(dataFB, FBApiReqFriendlyName=None, docID=None, requireGraphql=None):
     
     if not hasattr(formAll, "counter"):
          formAll.counter = 0
     formAll.counter += 1
     __reg = formAll.counter
     
     dataForm = {}
     
     if (requireGraphql == None):
          dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
          dataForm["jazoest"] = dataFB["jazoest"]
          dataForm["__a"] = 1
          dataForm["__user"] = str(dataFB["FacebookID"])
          dataForm["__req"] = str_base(__reg, 36) 
          dataForm["__rev"] = dataFB["clientRevision"]
          dataForm["av"] = dataFB["FacebookID"]
          dataForm["fb_api_caller_class"] = "RelayModern"
          dataForm["fb_api_req_friendly_name"] = FBApiReqFriendlyName
          dataForm["server_timestamps"] = "true"
          dataForm["doc_id"] = str(docID)
     else:
          dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
          dataForm["jazoest"] = dataFB["jazoest"]
          dataForm["__a"] = 1
          dataForm["__user"] = str(dataFB["FacebookID"])
          dataForm["__req"] = str_base(__reg, 36) 
          dataForm["__rev"] = dataFB["clientRevision"]
          dataForm["av"] = dataFB["FacebookID"]

     return dataForm
     
def clearHTML(text):
     regex = re.compile(r'<[^>]+>')
     return regex.sub('', text)
     
def mainRequests(urlRequests, dataForm, setCookies):
     return {
          "headers": Headers(setCookies, dataForm),
          "timeout": 5,
          "url": urlRequests, 
          "data": dataForm,
          "cookies": parse_cookie_string(setCookies),
          "verify": True
     }
     
def generate_session_id():
     """Generate a random session ID between 1 and 9007199254740991."""
     return random.randint(1, 2 ** 53)  

def generate_client_id():
     def gen(length):
          return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
     return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)
     
def json_minimal(data):
     """Get JSON data in minimal form."""
     return json.dumps(data, separators=(",", ":"))

def _set_chat_on(value):
     return json_minimal(value)

def gen_threading_id():
     return str(
          int(format(int(time.time() * 1000), "b") + 
          ("0000000000000000000000" + 
          format(int(random.random() * 4294967295), "b"))
          [-22:], 2)
     )

def require_list(list_):
     if isinstance(list_, list):
          return set(list_)
     else:
          return set([list_])

def get_files_from_paths(filenames):
     files = [filenames, open(filenames, "rb"), guess_type(filenames)[0]]
     yield files


# --------- integrated_add_user.py nội dung -----------

class FacebookGroupManager:
    def __init__(self, dataFB):
        """
        Initialize với data Facebook từ dataGetHome()
        
        Args:
            dataFB: Dictionary chứa thông tin FB (fb_dtsg, jazoest, FacebookID, etc.)
        """
        self.dataFB = dataFB
    
    def add_user_to_group(self, user_ids, thread_id):
        """
        Thêm user vào group chat
        
        Args:
            user_ids: List các Facebook ID cần thêm vào group hoặc string một ID
            thread_id: ID của thread/group cần thêm user vào
            
        Returns:
            dict: Kết quả thực hiện
        """
        try:
            if isinstance(user_ids, str):
                user_ids = [user_ids]
            
            offline_threading_id = gen_threading_id()
            threading_id = gen_threading_id()
            timestamp = int(time.time() * 1000)
            
            form_data = {
                "client": "mercury",
                "action_type": "ma-type:log-message",
                "author": f"fbid:{self.dataFB['FacebookID']}",
                "thread_id": thread_id,   # sửa thread_id cho đúng
                "timestamp": timestamp,
                "timestamp_absolute": "Today",
                "timestamp_relative": self._generate_timestamp_relative(),
                "timestamp_time_passed": "0",
                "is_unread": False,
                "is_cleared": False,
                "is_forward": False,
                "is_filtered_content": False,
                "is_filtered_content_bh": False,
                "is_filtered_content_account": False,
                "is_spoof_warning": False,
                "source": "source:chat:web",
                "source_tags[0]": "source:chat",
                "log_message_type": "log:subscribe",
                "status": "0",
                "offline_threading_id": offline_threading_id,
                "message_id": offline_threading_id,
                "threading_id": threading_id,
                "manual_retry_cnt": "0",
                "thread_fbid": thread_id,
                "fb_dtsg": self.dataFB["fb_dtsg"],
                "jazoest": self.dataFB["jazoest"],
                "__user": self.dataFB["FacebookID"],
                "__a": "1",
                "__req": "1",
                "__rev": self.dataFB.get("clientRevision", "1015919737")
            }
            
            for idx, user_id in enumerate(user_ids):
                form_data[f"log_message_data[added_participants][{idx}]"] = f"fbid:{user_id}"
            
            response = requests.post(
                **mainRequests(
                    "https://www.facebook.com/messaging/send/", 
                    form_data, 
                    self.dataFB["cookieFacebook"]
                )
            )
            
            result = self._parse_response(response)
            
            return {
                "success": True,
                "message": f"Đã thêm {len(user_ids)} user vào group",
                "users_added": user_ids,
                "thread_id": thread_id,
                "response_data": result,
                "processing_time": response.elapsed.total_seconds()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Lỗi khi thêm user vào group"
            }
    
    def add_user_to_group_graphql(self, user_ids, thread_id):
        """
        Thêm user vào group bằng GraphQL API (phương pháp thay thế)
        
        Args:
            user_ids: List các Facebook ID cần thêm vào group hoặc string một ID
            thread_id: ID của thread/group cần thêm user vào
            
        Returns:
            dict: Kết quả thực hiện
        """
        try:
            if isinstance(user_ids, str):
                user_ids = [user_ids]
            
            form_data = formAll(
                self.dataFB, 
                FBApiReqFriendlyName="MessengerGroupAddParticipantMutation",
                docID="1753266014707682"
            )
            
            variables = {
                "input": {
                    "thread_fbid": thread_id,
                    "participant_ids": user_ids,
                    "client_mutation_id": gen_threading_id()
                }
            }
            
            form_data["variables"] = json.dumps(variables)
            
            response = requests.post(
                **mainRequests(
                    "https://www.facebook.com/api/graphql/", 
                    form_data, 
                    self.dataFB["cookieFacebook"]
                )
            )
            
            result = self._parse_response(response)
            
            return {
                "success": True,
                "method": "GraphQL",
                "message": f"Đã thêm {len(user_ids)} user vào group",
                "users_added": user_ids,
                "thread_id": thread_id,
                "response_data": result,
                "processing_time": response.elapsed.total_seconds()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Lỗi khi thêm user vào group bằng GraphQL"
            }
    
    def bulk_add_users(self, user_list, thread_id, batch_size=5, delay=2):
        """
        Thêm nhiều user vào group theo batch để tránh bị block
        
        Args:
            user_list: List các Facebook ID cần thêm
            thread_id: ID của thread/group
            batch_size: Số user thêm mỗi lần (default: 5)
            delay: Thời gian chờ giữa các batch (giây, default: 2)
            
        Returns:
            dict: Kết quả tổng hợp
        """
        results = []
        success_count = 0
        failed_count = 0
        
        for i in range(0, len(user_list), batch_size):
            batch = user_list[i:i + batch_size]
            
            print(f"Đang thêm batch {i//batch_size + 1}: {len(batch)} users")
            
            result = self.add_user_to_group(batch, thread_id)
            results.append(result)
            
            if result["success"]:
                success_count += len(batch)
                print(f"✅ Thành công: {len(batch)} users")
            else:
                failed_count += len(batch)
                print(f"❌ Thất bại: {result['message']}")
            
            if i + batch_size < len(user_list):
                print(f"Chờ {delay} giây...")
                time.sleep(delay)
        
        return {
            "total_users": len(user_list),
            "success_count": success_count,
            "failed_count": failed_count,
            "batch_results": results,
            "summary": f"Đã thêm {success_count}/{len(user_list)} users thành công"
        }
    
    def _generate_timestamp_relative(self):
        now = time.time()
        return str(int(now))
    
    def _parse_response(self, response):
        try:
            if response.status_code == 200:
                if response.text.startswith('for (;;);'):
                    json_text = response.text[9:]
                else:
                    json_text = response.text
                
                try:
                    return json.loads(json_text)
                except:
                    return {"raw_response": response.text[:500]}
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                }
        except Exception as e:
            return {"parse_error": str(e)}


def quick_add_user(dataFB, user_ids, thread_id):
    """
    Hàm nhanh để thêm user vào group
    
    Args:
        dataFB: Data Facebook từ dataGetHome()
        user_ids: List hoặc string Facebook ID
        thread_id: ID của group/thread
        
    Returns:
        dict: Kết quả
    """
    manager = FacebookGroupManager(dataFB)
    return manager.add_user_to_group(user_ids, thread_id)
# ===== UTILS =====

def digitToChar(digit):
    if digit < 10:
        return str(digit)
    return chr(ord("a") + digit - 10)

def gen_threading_id():
    return str(
        int(format(int(time.time() * 1000), "b") +
        ("0000000000000000000000" +
        format(int(random.random() * 4294967295), "b"))[-22:], 2)
    )

def str_base(number, base):
    if number < 0:
        return "-" + str_base(-number, base)
    (d, m) = divmod(number, base)
    if d > 0:
        return str_base(d, base) + digitToChar(m)
    return digitToChar(m)

def parse_cookie_string(cookie_string):
    cookie_dict = {}
    cookies = cookie_string.split(";")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict

def Headers(setCookies, dataForm=None, Host=None):
    if Host is None:
        Host = "www.facebook.com"
    headers = {
        "Host": Host,
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
        "Origin": f"https://{Host}",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"https://{Host}",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    if dataForm is not None:
        headers["Content-Length"] = str(len(str(dataForm)))
    return headers

def generate_session_id():
    return random.randint(1, 2 ** 53)

def generate_client_id():
    def gen(length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)

def formAll(dataFB, FBApiReqFriendlyName=None, docID=None, requireGraphql=None):
    __reg = getattr(formAll, 'counter', 0)
    formAll.counter = __reg + 1
    dataForm = {
        "fb_dtsg": dataFB["fb_dtsg"],
        "jazoest": dataFB["jazoest"],
        "__a": 1,
        "__user": str(dataFB["FacebookID"]),
        "__req": str_base(__reg, 36),
        "__rev": dataFB["clientRevision"],
        "av": dataFB["FacebookID"]
    }
    if requireGraphql is None:
        dataForm.update({
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": FBApiReqFriendlyName,
            "server_timestamps": "true",
            "doc_id": str(docID)
        })
    return dataForm

def mainRequests(urlRequests, dataForm, setCookies):
    return {
        "headers": Headers(setCookies, dataForm),
        "timeout": 60,
        "url": urlRequests,
        "data": dataForm,
        "cookies": parse_cookie_string(setCookies),
        "verify": True
    }

# ===== Facebook Data Extractor =====

def dataGetHome(setCookies):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
        "Mozilla/5.0 (X11; Linux x86_64)"
    ]
    dictValueSaved = {}
    try:
        c_user = re.search(r"c_user=(\d+)", setCookies)
        dictValueSaved["FacebookID"] = c_user.group(1) if c_user else "Unknown"
    except:
        dictValueSaved["FacebookID"] = "Unknown"

    headers = {
        'Cookie': setCookies,
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html',
        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Upgrade-Insecure-Requests': '1'
    }

    params = {
        "fb_dtsg": None,
        "jazoest": None,
        "fb_dtsg_ag": None,
        "hash": None,
        "sessionID": None,
        "clientRevision": None
    }

    for url in ['https://www.facebook.com', 'https://m.facebook.com']:
        try:
            res = requests.get(url, headers=headers, timeout=30)
            html = res.text
            if not params["fb_dtsg"]:
                match = re.search(r'"token":"(.*?)"', html) or re.search(r'name="fb_dtsg" value="(.*?)"', html)
                if match:
                    params["fb_dtsg"] = match.group(1)
            if not params["jazoest"]:
                match = re.search(r'jazoest=(\d+)', html)
                if match:
                    params["jazoest"] = match.group(1)
            if not params["clientRevision"]:
                match = re.search(r'client_revision":(\d+)', html)
                if match:
                    params["clientRevision"] = match.group(1)
        except:
            continue

    dictValueSaved.update({
        **params,
        "cookieFacebook": setCookies,
        "__rev": "1015919737",
        "__req": "1b",
        "__a": "1"
    })

    return dictValueSaved


# ===== Facebook Block Tool =====

class FacebookBlockTool:
    def __init__(self, cookie_facebook):
        self.cookie_facebook = cookie_facebook
        self.dataFB = dataGetHome(cookie_facebook)

    def block_user(self, user_id):
        return self._interact_block_unblock(user_id, "block")

    def unblock_user(self, user_id):
        return self._interact_block_unblock(user_id, "unblock")

    def _interact_block_unblock(self, user_id, action):
        if not self.dataFB:
            return {"error": 1, "messages": "Chưa khởi tạo dữ liệu."}

        if action == "block":
            friendly_name = "ProfileCometActionBlockUserMutation"
            doc_id = "6305880099497989"
            variables = json.dumps({
                "input": {
                    "blocksource": "PROFILE",
                    "user_id": int(user_id),
                    "actor_id": self.dataFB["FacebookID"],
                    "client_mutation_id": str(random.randint(1000, 9999))
                },
                "scale": 3
            })
        elif action == "unblock":
            friendly_name = "BlockingSettingsBlockMutation"
            doc_id = "6009824239038988"
            variables = json.dumps({
                "input": {
                    "block_action": "UNBLOCK",
                    "setting": "USER",
                    "target_id": str(user_id),
                    "actor_id": self.dataFB["FacebookID"],
                    "client_mutation_id": "1"
                }
            })
        else:
            return {"error": 1, "messages": "Hành động không hợp lệ."}

        data_form = formAll(self.dataFB, friendly_name, doc_id)
        data_form["variables"] = variables

        try:
            response = requests.post(
                **mainRequests("https://www.facebook.com/api/graphql/", data_form, self.dataFB["cookieFacebook"])
            )
            res_data = json.loads(response.text)
            if "data" in res_data:
                return {"success": 1, "messages": "Thành công", "action": action}
            else:
                return {"error": 1, "messages": "Thất bại", "details": res_data.get("errors")}
        except Exception as e:
            return {"error": 1, "messages": f"Lỗi gửi request: {e}"}


# ===== TÊN BOX (ĐỔI TÊN NHÓM CHAT) =====
def tenbox(newTitle, threadID, dataFB):
    if not newTitle or not threadID or not dataFB:
        return {
            "success": False,
            "error": "Thiếu thông tin bắt buộc: newTitle, threadID, hoặc dataFB"
        }
    try:
        messageAndOTID = gen_threading_id()
        current_timestamp = int(time.time() * 1000)
        form_data = {
            "client": "mercury",
            "action_type": "ma-type:log-message",
            "author": f"fbid:{dataFB['FacebookID']}",
            "thread_id": str(threadID),
            "timestamp": current_timestamp,
            "timestamp_relative": str(int(time.time())),
            "source": "source:chat:web",
            "source_tags[0]": "source:chat",
            "offline_threading_id": messageAndOTID,
            "message_id": messageAndOTID,
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
        url = "https://www.facebook.com/messaging/set_thread_name/"
        response = requests.post(**mainRequests(url, form_data, dataFB["cookieFacebook"]))
        if response.status_code == 200:
            try:
                response_data = response.json()
                if "error" in response_data:
                    return {
                        "success": False,
                        "error": f"Lỗi từ Facebook: {response_data.get('error')}"
                    }
                return {
                    "success": True,
                    "message": f"Đã đổi tên thành: {newTitle}"
                }
            except:
                return {
                    "success": True,
                    "message": f"Đã đổi tên thành: {newTitle} (parse JSON lỗi)"
                }
        else:
            return {
                "success": False,
                "error": f"HTTP Error: {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def tenboxWithFbTools(newTitle, threadID, setCookies):
    try:
        dataFB = dataGetHome(setCookies)
        if "FacebookID" not in dataFB:
            return {
                "success": False,
                "error": "Không thể lấy data Facebook, cookie có thể đã hết hạn."
            }
        return tenbox(newTitle, threadID, dataFB)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ===== ĐOẠN CHẠY KIỂM TRA (main) =====
if __name__ == "__main__":
    file_path = input("Nhập FILE chứa cookies (mỗi cookies xuống hàng 1 lần): ").strip()
    thread_id = input("Nhập ID BOX cần đổi tên: ").strip()
    try:
        delay = float(input("Nhập DELAY (giây): ").strip())
    except:
        delay = 3.0
    name_list = [
    "name1",
    "name2"
    ]
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            cookies_list = [line.strip() for line in f if line.strip()]
    except:
        print("Không thể đọc file cookie!")
        exit()

    if not cookies_list:
        print("File cookie rỗng!")
        exit()

    name_index = 0
    while True:
        for cookie in cookies_list:
            name = name_list[name_index]
            print(f"\n>>> Đang đổi tên thành: {name}")
            result = tenboxWithFbTools(name, thread_id, cookie)
            print(json.dumps(result, indent=2, ensure_ascii=False))

            name_index = (name_index + 1) % len(name_list)

            sleep_time = delay + random.uniform(0, 1)
            print(f"Đợi {sleep_time:.2f} giây...")
            time.sleep(sleep_time)