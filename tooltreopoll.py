import os, time, json, sys
from zlapi import ZaloAPI
from zlapi.models import Message, Mention
from pyfiglet import figlet_format

def show_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = figlet_format("ZALO POLL", font="slant")
    print(banner)
    print("TOOL SPAM POLL + TAG".center(60))
    print("=" * 60)

def parse_selection(input_str, max_index):
    try:
        return [int(i.strip()) for i in input_str.split(',') if 1 <= int(i.strip()) <= max_index]
    except:
        print("❌ Định dạng STT không hợp lệ!")
        return []

def parse_cookie_string(cookie_str):
    try:
        cleaned = cookie_str.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print("❌ Cookie không hợp lệ!")
        return None

class Bot(ZaloAPI):
    def __init__(self, imei, session_cookies):
        super().__init__('api_key', 'secret_key', imei, session_cookies)

    def fetch_groups(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id in all_groups.gridVerMap:
                group_info = self.fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({'id': group_id, 'name': group_name})
            return group_list
        except Exception as e:
            print(f"❌ Lỗi lấy nhóm: {e}")
            return []

    def fetch_members(self, group_id):
        try:
            group_info = self.fetchGroupInfo(group_id)
            mem_ver_list = group_info.gridInfoMap[group_id]["memVerList"]
            member_ids = [mem.split("_")[0] for mem in mem_ver_list]
            members = []
            for uid in member_ids:
                try:
                    user_info = self.fetchUserInfo(uid)
                    user_data = user_info.changed_profiles[uid]
                    members.append({'id': user_data['userId'], 'name': user_data['displayName']})
                except:
                    members.append({'id': uid, 'name': f"User_{uid}"})
            return members
        except Exception as e:
            print(f"❌ Lỗi lấy thành viên: {e}")
            return []

# === MAIN ===
if __name__ == "__main__":
    show_banner()

    imei = input("🔑 Nhập IMEI: ").strip()
    cookie_str = input("🍪 Nhập Cookie JSON: ").strip()
    cookies = parse_cookie_string(cookie_str)
    if not cookies:
        sys.exit()

    bot = Bot(imei, cookies)
    groups = bot.fetch_groups()

    if not groups:
        print("⚠️ Không tìm thấy nhóm.")
        sys.exit()

    print("\n📋 Danh sách nhóm:")
    for i, g in enumerate(groups, 1):
        print(f"{i}. {g['name']} | ID: {g['id']}")

    pick = input("👉 Nhập STT nhóm muốn gửi poll: ").strip()
    selected_indexes = parse_selection(pick, len(groups))
    if not selected_indexes:
        sys.exit()

    poll_file = input("📁 Nhập tên file chứa lựa chọn poll (vd: abc.txt): ").strip()
    if not os.path.exists(poll_file):
        print("❌ File không tồn tại.")
        sys.exit()

    try:
        with open("nhay.txt", "r", encoding="utf-8") as f:
            questions = [line.strip() for line in f if line.strip()]
    except:
        print("❌ Không tìm thấy nhay.txt")
        sys.exit()

    try:
        with open(poll_file, "r", encoding="utf-8") as f:
            poll_options = [line.strip() for line in f if line.strip()]
    except:
        print(f"❌ Không thể đọc {poll_file}")
        sys.exit()

    delay = input("⏳ Delay giữa mỗi poll (giây): ").strip()
    try:
        delay = float(delay)
    except:
        delay = 1.0

    # Lưu lại danh sách thành viên đã chọn để tag
    tag_map = {}

    for idx in selected_indexes:
        group = groups[idx - 1]
        members = bot.fetch_members(group['id'])
        print(f"\n👥 Thành viên nhóm {group['name']}:")
        for i, m in enumerate(members, 1):
            print(f"{i}. {m['name']} | ID: {m['id']}")

        tag_input = input("👉 STT thành viên để tag (vd: 1,2,3): ").strip()
        tag_indexes = parse_selection(tag_input, len(members))
        tag_users = [members[i - 1] for i in tag_indexes]
        tag_map[group['id']] = {
            'info': group,
            'members': tag_users
        }

    print("\n🚀 BẮT ĐẦU SPAM VÔ HẠN...\nẤn Ctrl + C để dừng!")

    try:
        while True:
            for group_id, data in tag_map.items():
                group = data['info']
                tag_users = data['members']
                for question in questions:
                    mention_text = " ".join([f"@{u['name']}" for u in tag_users])
                    poll_text = f"{mention_text} {question}"
                    try:
                        bot.createPoll(question=poll_text, options=poll_options, groupId=group['id'])
                        print(f"📤 Gửi poll tới nhóm {group['name']}: {poll_text}")
                    except Exception as e:
                        print(f"❌ Lỗi gửi poll: {e}")
                    time.sleep(delay)
    except KeyboardInterrupt:
        print("\n⛔ Đã dừng spam.")
        sys.exit()