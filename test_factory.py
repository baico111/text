import sys
import os
import time
import json
import requests
import base64
import datetime

# --- 核心环境变量 ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")
ZEABUR_AI_URL = os.environ.get("ZEABUR_AI_URL") 
HOSTUUID = os.environ.get("HOSTUUID")

if not HOSTUUID or not ZEABUR_AI_URL:
    print("[-] 错误：环境变量配置不全", file=sys.stderr)
    sys.exit(1)

TARGET_URL = f"https://host2play.gratis/server/renew?i={HOSTUUID}"

def send_tg_report_with_photo(status_text, elapsed, photo_path, token=""):
    beijing_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    display_token = (token[:25] + "...") if token else "无"
    
    caption = (
        f"🛠️ <b>视觉工厂 - 穿透实况报告</b>\n"
        f"————————————————————\n"
        f"🛰️ <b>任务状态:</b> {status_text}\n"
        f"⏱️ <b>总计耗时:</b> {elapsed}\n"
        f"🔑 <b>Token摘要:</b> <code>{display_token}</code>\n"
        f"🕒 <b>北京时间:</b> {beijing_time}\n"
        f"————————————————————"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                requests.post(url, data={'chat_id': MY_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': photo}, timeout=20)
        else:
            text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(text_url, data={'chat_id': MY_CHAT_ID, 'text': caption, 'parse_mode': 'HTML'}, timeout=15)
    except: pass

def run_test():
    print(f"[*] 正在向远程视觉工厂发起穿透请求...", file=sys.stderr)
    
    # --- 核心优化点：注入触发点击指令 ---
    payload = {
        "url": TARGET_URL,
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "cookies": [],
        # 告诉 main.py：进去之后先帮我点这个按钮，验证码才会出来
        "pre_click": "text='Renew server'", 
        "wait_before_captcha": 3  # 点击后等 3 秒让验证码弹出
    }
    
    start_time = time.time()
    try:
        response = requests.post(ZEABUR_AI_URL, json=payload, timeout=120)
        elapsed = f"{time.time() - start_time:.2f}s"
        
        if response.status_code == 200:
            res_data = response.json()
            photo_file = "factory_live_shot.png"
            has_photo = False
            
            if res_data.get("screenshot"):
                try:
                    with open(photo_file, "wb") as f:
                        f.write(base64.b64decode(res_data.get("screenshot")))
                    has_photo = True
                except: pass

            if res_data.get("success"):
                token = res_data.get("token")
                print(f"[+ SUCCESS] 穿透成功！", file=sys.stderr)
                send_tg_report_with_photo("穿透成功 ✅", elapsed, photo_file if has_photo else "", token)
                return True
            else:
                error_msg = res_data.get("error", "AI 判定失败或未拿到 Token")
                print(f"[-] 穿透失败: {error_msg}", file=sys.stderr)
                send_tg_report_with_photo(f"穿透失败 ❌ ({error_msg})", elapsed, photo_file if has_photo else "")
        else:
            print(f"[-] 服务器异常: {response.status_code}", file=sys.stderr)
            send_tg_report_with_photo(f"服务器异常 ⚠️ ({response.status_code})", f"{time.time()-start_time:.2f}s", "")
            
    except Exception as e:
        print(f"[-] 请求异常: {e}", file=sys.stderr)
        send_tg_report_with_photo("通信崩溃/超时 ⚠️", f"{time.time()-start_time:.2f}s", "")
    
    return False

if __name__ == "__main__":
    if run_test():
        print("[*] 任务圆满完成。")
    else:
        sys.exit(1)
