# toolrnboxzl.py
import json
import time
from zlapi import ZaloAPI

class ZaloRenameBot(ZaloAPI):
    def __init__(self, imei, cookies):
        super().__init__('api_key', 'secret_key', imei, cookies)

    def fetch_groups(self):
        try:
            all_groups = self.fetchAllGroups().gridVerMap
            group_list = []
            for group_id in all_groups:
                info = self.fetchGroupInfo(group_id)
                group_name = info.gridInfoMap[group_id]["name"]
                group_list.append({"id": group_id, "name": group_name})
            return group_list
        except Exception as e:
            print(f"❌ Lỗi lấy nhóm: {e}")
            return []

    def rename_loop(self, group_id, delay, stop_event):
        try:
            with open("nhay.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("❌ Không tìm thấy file nhay.txt")
            return

        if not lines:
            print("❌ File nhay.txt không có nội dung!")
            return

        while not stop_event.is_set():
            for line in lines:
                if stop_event.is_set():
                    return
                try:
                    self.changeGroupName(line, group_id)
                    print(f"✅ Đã đổi tên nhóm thành: {line}")
                except Exception as e:
                    print(f"❌ Lỗi đổi tên: {e}")
                time.sleep(delay)