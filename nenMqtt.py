import json
import random
import time
import hashlib
from typing import Callable, Optional
import paho.mqtt.client as mqtt
from urllib.parse import urlparse
import ssl

# ================== HÀM TIỆN ÍCH (thay cho utils.py) ==================
def generate_offline_threading_id() -> str:
    """Tạo ID offline threading giống Facebook"""
    return str(int(time.time() * 1000)) + str(random.randint(1000, 9999))

def json_minimal(data) -> str:
    """Chuyển dict -> JSON rút gọn"""
    return json.dumps(data, separators=(",", ":"))

def parse_cookie_string(cookie_string: str) -> dict:
    """Parse cookie string thành dict"""
    cookies = {}
    for part in cookie_string.split(";"):
        if "=" in part:
            key, value = part.strip().split("=", 1)
            cookies[key] = value
    return cookies

def generate_session_id() -> str:
    """Tạo session id"""
    return hashlib.md5(str(time.time()).encode()).hexdigest()

def generate_client_id() -> str:
    """Tạo client id random"""
    return str(random.randint(10**14, 10**15 - 1))

THEMES = [
    {"id": "3650637715209675", "name": "Besties"},
    {"id": "769656934577391", "name": "Women's History Month"},
    {"id": "702099018755409", "name": "Dune: Part Two"},
    {"id": "1480404512543552", "name": "Avatar: The Last Airbender"},
    {"id": "952656233130616", "name": "J.Lo"},
    {"id": "741311439775765", "name": "Love"},
    {"id": "215565958307259", "name": "Bob Marley: One Love"},
    {"id": "194982117007866", "name": "Football"},
    {"id": "1743641112805218", "name": "Soccer"},
    {"id": "730357905262632", "name": "Mean Girls"},
    {"id": "1270466356981452", "name": "Wonka"},
    {"id": "704702021720552", "name": "Pizza"},
    {"id": "1013083536414851", "name": "Wish"},
    {"id": "359537246600743", "name": "Trolls"},
    {"id": "173976782455615", "name": "The Marvels"},
    {"id": "2317258455139234", "name": "One Piece"},
    {"id": "6685081604943977", "name": "1989"},
    {"id": "1508524016651271", "name": "Avocado"},
    {"id": "265997946276694", "name": "Loki Season 2"},
    {"id": "6584393768293861", "name": "olivia rodrigo"},
    {"id": "845097890371902", "name": "Baseball"},
    {"id": "292955489929680", "name": "Lollipop"},
    {"id": "976389323536938", "name": "Loops"},
    {"id": "810978360551741", "name": "Parenthood"},
    {"id": "195296273246380", "name": "Bubble Tea"},
    {"id": "6026716157422736", "name": "Basketball"},
    {"id": "693996545771691", "name": "Elephants & Flowers"},
    {"id": "390127158985345", "name": "Chill"},
    {"id": "365557122117011", "name": "Support"},
    {"id": "339021464972092", "name": "Music"},
    {"id": "1060619084701625", "name": "Lo-Fi"},
    {"id": "3190514984517598", "name": "Sky"},
    {"id": "627144732056021", "name": "Celebration"},
    {"id": "275041734441112", "name": "Care"},
    {"id": "3082966625307060", "name": "Astrology"},
    {"id": "539927563794799", "name": "Cottagecore"},
    {"id": "527564631955494", "name": "Ocean"},
    {"id": "230032715012014", "name": "Tie-Dye"},
    {"id": "788274591712841", "name": "Monochrome"},
    {"id": "3259963564026002", "name": "Default"},
    {"id": "724096885023603", "name": "Berry"},
    {"id": "624266884847972", "name": "Candy"},
    {"id": "273728810607574", "name": "Unicorn"},
    {"id": "262191918210707", "name": "Tropical"},
    {"id": "2533652183614000", "name": "Maple"},
    {"id": "909695489504566", "name": "Sushi"},
    {"id": "582065306070020", "name": "Rocket"},
    {"id": "557344741607350", "name": "Citrus"},
    {"id": "280333826736184", "name": "Lollipop"},
    {"id": "271607034185782", "name": "Shadow"},
    {"id": "1257453361255152", "name": "Rose"},
    {"id": "571193503540759", "name": "Lavender"},
    {"id": "2873642949430623", "name": "Tulip"},
    {"id": "3273938616164733", "name": "Classic"},
    {"id": "403422283881973", "name": "Apple"},
    {"id": "3022526817824329", "name": "Peach"},
    {"id": "672058580051520", "name": "Honey"},
    {"id": "3151463484918004", "name": "Kiwi"},
    {"id": "736591620215564", "name": "Ocean"},
    {"id": "193497045377796", "name": "Grape"}
]


class MQTTThemeClient:
    """Client để kết nối MQTT và gửi set theme"""
    
    def __init__(self, cookies: str):
        self.cookies = cookies
        self.mqtt_client = None
        self.is_connected = False
        self.user_id = None
        self.ws_req_number = 0
        self.ws_task_number = 0
        self.req_callbacks = {}
        
        # Extract user ID from cookies
        cookie_dict = parse_cookie_string(cookies)
        if "c_user" in cookie_dict:
            self.user_id = cookie_dict["c_user"]
        else:
            raise ValueError("Không tìm thấy user ID trong cookies")
    
    def connect(self):
        """Kết nối tới MQTT server"""
        if self.is_connected:
            print("MQTT connection is now available")
            return
            
        print("Connecting to MQTT... ")
        
        # Generate session info
        session_id = generate_session_id()
        client_id = generate_client_id()
        
        # User info for MQTT
        user_info = {
            "u": self.user_id,
            "s": session_id,
            "chat_on": True,
            "fg": False,
            "d": client_id,
            "ct": "websocket",
            "aid": "219994525426954",
            "mqtt_sid": "",
            "cp": 3,
            "ecp": 10,
            "st": [],
            "pm": [],
            "dc": "",
            "no_auto_fg": True,
            "gas": None,
            "pack": []
        }
        
        # MQTT host
        host = f"wss://edge-chat.facebook.com/chat?sid={session_id}&cid={client_id}"
        
        # Headers
        cookie_dict = parse_cookie_string(self.cookies)
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
        
        # Create MQTT client
        self.mqtt_client = mqtt.Client(
            client_id="mqttwsclient",
            clean_session=True,
            protocol=mqtt.MQTTv31,
            transport="websockets"
        )
        
        # SSL setup
        self.mqtt_client.tls_set(
            certfile=None, 
            keyfile=None, 
            cert_reqs=ssl.CERT_NONE, 
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        self.mqtt_client.tls_insecure_set(True)
        
        # Set username
        self.mqtt_client.username_pw_set(username=json_minimal(user_info))
        
        # WebSocket options
        parsed_host = urlparse(host)
        self.mqtt_client.ws_set_options(
            path=f"{parsed_host.path}?{parsed_host.query}",
            headers={
                "Cookie": cookie_str,
                "Origin": "https://www.facebook.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                "Referer": "https://www.facebook.com/",
                "Host": "edge-chat.facebook.com"
            }
        )
        
        # Event handlers
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("MQTT connection successfull")
                self.is_connected = True
                # Subscribe to necessary topics
                client.subscribe("/ls_resp", qos=1)
            else:
                print(f"MQTT connection failed : {rc}")
                
        def on_disconnect(client, userdata, rc):
            print(f"Disconnect MQTT : {rc}")
            self.is_connected = False
            
        def on_message(client, userdata, msg):
            # Xử lý response từ server nếu cần
            if msg.topic == "/ls_resp":
                try:
                    payload_str = msg.payload.decode("utf-8")
                    if payload_str.startswith("{"):
                        response = json.loads(payload_str)
                        req_id = response.get("request_id")
                        if req_id in self.req_callbacks:
                            callback = self.req_callbacks[req_id]
                            if callback:
                                callback(response)
                            del self.req_callbacks[req_id]
                except:
                    pass
        
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_disconnect = on_disconnect
        self.mqtt_client.on_message = on_message
        
        # Connect
        try:
            self.mqtt_client.connect("edge-chat.facebook.com", 443, 10)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            import time
            timeout = 10
            while not self.is_connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            if not self.is_connected:
                raise Exception("Timeout khi kết nối MQTT")
                
        except Exception as e:
            raise Exception(f"Lỗi kết nối MQTT: {str(e)}")
    
    def disconnect(self):
        """Ngắt kết nối MQTT"""
        if self.mqtt_client and self.is_connected:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.is_connected = False
            print("MQTT connection disconnected")
    
    def get_theme_by_name(self, name: str) -> Optional[dict]:
        """Tìm theme theo tên"""
        for theme in THEMES:
            if theme["name"].lower() == name.lower():
                return theme
        return None
        
    def get_random_theme(self) -> dict:
        """Lấy theme ngẫu nhiên"""
        return random.choice(THEMES)
    
    def set_theme(self, thread_id: str, theme_id: Optional[str] = None, theme_name: Optional[str] = None, callback: Optional[Callable] = None) -> str:
        """
        Set theme cho thread
        
        Args:
            thread_id: ID của thread
            theme_id: ID của theme (ưu tiên hơn theme_name)
            theme_name: Tên của theme
            callback: Callback function khi hoàn thành
            
        Returns:
            ID của theme đã set
        """
        if not self.is_connected:
            raise Exception("Chưa kết nối MQTT! Hãy gọi connect() trước")
            
        # Xác định theme ID
        selected_theme_id = None
        selected_theme_name = None
        
        if theme_id:
            # Kiểm tra theme_id có hợp lệ không
            theme_exists = any(theme["id"] == theme_id for theme in THEMES)
            if theme_exists:
                selected_theme_id = theme_id
                selected_theme = next((theme for theme in THEMES if theme["id"] == theme_id), None)
                selected_theme_name = selected_theme["name"] if selected_theme else "Unknown"
            else:
                raise ValueError(f"Theme ID '{theme_id}' không tồn tại")
                
        elif theme_name:
            # Tìm theme theo tên
            theme = self.get_theme_by_name(theme_name)
            if theme:
                selected_theme_id = theme["id"]
                selected_theme_name = theme["name"]
            else:
                raise ValueError(f"Theme '{theme_name}' không tồn tại")
        else:
            # Chọn theme ngẫu nhiên
            random_theme = self.get_random_theme()
            selected_theme_id = random_theme["id"]
            selected_theme_name = random_theme["name"]
            
        # Tăng request numbers
        self.ws_req_number += 1
        self.ws_task_number += 1
        
        # Tạo task payload
        task_payload = {
            "thread_key": thread_id,
            "theme_fbid": selected_theme_id,
            "source": None,
            "sync_group": 1,
            "payload": None
        }
        
        task = {
            "failure_count": None,
            "label": "43",
            "payload": json_minimal(task_payload),
            "queue_name": "thread_theme",
            "task_id": self.ws_task_number
        }
        
        content = {
            "app_id": "2220391788200892",
            "payload": json_minimal({
                "data_trace_id": None,
                "epoch_id": int(generate_offline_threading_id()),
                "tasks": [task],
                "version_id": "25095469420099952"
            }),
            "request_id": self.ws_req_number,
            "type": 3
        }
        
        # Lưu callback nếu có
        if callback and callable(callback):
            self.req_callbacks[self.ws_req_number] = callback
            
        # Gửi qua MQTT
        self.mqtt_client.publish(
            topic="/ls_req",
            payload=json_minimal(content),
            qos=1,
            retain=False
        )
        
        return selected_theme_id

# Hàm tiện ích
def list_all_themes():
    """Liệt kê tất cả themes có sẵn"""
    print("📝 Danh sách themes có sẵn:")
    for i, theme in enumerate(THEMES, 1):
        print(f"{i:2d}. {theme['name']} (ID: {theme['id']})")

def find_theme_by_name(name: str) -> Optional[dict]:
    """Tìm theme theo tên"""
    for theme in THEMES:
        if theme["name"].lower() == name.lower():
            return theme
    return None

# Ví dụ sử dụng
if __name__ == "__main__":
    # Sử dụng
    cookies = "your_facebook_cookies_here"
    
    # Tạo client
    client = MQTTThemeClient(cookies)
    
    try:
        # Kết nối
        client.connect()
        
        # Set theme ngẫu nhiên
        client.set_theme("thread_id_here")
        
        # Set theme bằng tên
        client.set_theme("thread_id_here", theme_name="Love")
        
        # Set theme bằng ID
        client.set_theme("thread_id_here", theme_id="741311439775765")
        
        # Set theme với callback
        def theme_callback(response):
            print(f"Response: {response}")
            
        client.set_theme("thread_id_here", theme_name="Ocean", callback=theme_callback)
        
        # Giữ connection một lúc để nhận response
        time.sleep(3)
        
    finally:
        # Ngắt kết nối
        client.disconnect()
    
    # Xem danh sách themes
    list_all_themes()
