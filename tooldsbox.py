import requests
import re
import json
import time
from rich import print
from rich.console import Console
from rich.table import Table

console = Console()

class FacebookSession:
    def __init__(self, cookie):
        self.cookie = cookie
        self.uid = self.get_uid()
        self.fb_dtsg, self.jazoest = self.init_params()

    def get_uid(self):
        try:
            return re.search(r"c_user=(\d+)", self.cookie).group(1)
        except:
            raise Exception("❌ Cookie không hợp lệ (thiếu c_user)")

    def init_params(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0'
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
                fb_dtsg = fb_dtsg_match.group(1)
                jazoest = jazoest_match.group(1) if jazoest_match else "22036"
                return fb_dtsg, jazoest
            else:
                raise Exception("❌ Không thể lấy được fb_dtsg")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi lấy fb_dtsg: {str(e)}")

def get_thread_list(cookie, limit=500):
    try:
        session = FacebookSession(cookie)
    except Exception as e:
        return {"error": str(e)}

    form_data = {
        "av": session.uid,
        "__user": session.uid,
        "fb_dtsg": session.fb_dtsg,
        "jazoest": session.jazoest,
        "__a": "1",
        "__req": "1b",
        "__rev": "1015919737",
        "__comet_req": "15",
        "__spin_r": "999999999",
        "__spin_b": "trunk",
        "__spin_t": str(int(time.time())),
    }

    queries = {
        "o0": {
            "doc_id": "3336396659757871",
            "query_params": {
                "limit": limit,
                "before": None,
                "tags": ["INBOX"],
                "includeDeliveryReceipts": False,
                "includeSeqID": True,
            }
        }
    }

    form_data["queries"] = json.dumps(queries)

    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-FB-Friendly-Name": "MessengerThreadListQuery",
    }

    try:
        response = requests.post(
            "https://www.facebook.com/api/graphqlbatch/",
            data=form_data,
            headers=headers,
            timeout=15
        )

        data_raw = response.text.split('{"successful_results"')[0]
        data = json.loads(data_raw)

        threads = data["o0"]["data"]["viewer"]["message_threads"]["nodes"]

        result = []
        for thread in threads:
            if not thread.get("thread_key") or not thread["thread_key"].get("thread_fbid"):
                continue
            result.append({
                "thread_id": thread["thread_key"]["thread_fbid"],
                "thread_name": thread.get("name") or "Không có tên"
            })

        return result

    except Exception as e:
        return {"error": f"❌ Lỗi khi lấy danh sách box: {e}"}

def main():
    console.rule("[bold green]TOOL LẤY DANH SÁCH BOX FACEBOOK")
    cookie = console.input("[bold yellow]🔐 Nhập cookie Facebook: [/]").strip()

    console.print("[blue]🔍 Đang lấy danh sách box...[/]")
    result = get_thread_list(cookie)

    if isinstance(result, dict) and "error" in result:
        console.print(f"[red]{result['error']}")
        return

    if not result:
        console.print("[red]❌ Không tìm thấy box nào!")
        return

    table = Table(title=f"[bold cyan]Danh sách {len(result)} box tìm được")
    table.add_column("STT", justify="right", style="green")
    table.add_column("Tên Box", style="white")
    table.add_column("ID Box", style="cyan")

    for i, thread in enumerate(result, 1):
        name = (thread.get("thread_name") or "Không có tên")[:50]
        table.add_row(str(i), name, thread["thread_id"])

    console.print(table)

if __name__ == "__main__":
    main()