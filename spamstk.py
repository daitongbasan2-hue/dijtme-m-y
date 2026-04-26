# spamstk.py

import time
from zlapi import ZaloAPI, ThreadType

class Bot(ZaloAPI):
    def __init__(self, imei, session_cookies):
        super().__init__('api_key', 'secret_key', imei, session_cookies)

    def fetch_groups(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id in all_groups.gridVerMap:
                try:
                    group_info = self.fetchGroupInfo(group_id)
                    group_name = group_info.gridInfoMap[group_id]["name"]
                    group_list.append({'id': group_id, 'name': group_name})
                    time.sleep(0.5)  # tránh rate-limit
                except Exception as e:
                    print(f"[!] Lỗi fetch group info: {e}")
                    continue
            return group_list
        except Exception as e:
            print(f"❌ Lỗi lấy danh sách nhóm: {e}")
            return []

    def spam_sticker_loop(self, group_id, group_name, sticker_id, cate_id, delay, stop_event):
        count = 0
        while not stop_event.is_set():
            try:
                self.sendSticker(
                    stickerType=7,
                    stickerId=sticker_id,
                    cateId=cate_id,
                    thread_id=group_id,
                    thread_type=ThreadType.GROUP
                )
                count += 1
                print(f"[{count}] 📤 Đã gửi sticker tới nhóm: {group_name}")
            except Exception as e:
                print(f"[!] Lỗi gửi sticker: {e}")
            time.sleep(delay)