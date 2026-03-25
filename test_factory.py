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
    """发送带截图的中文 TG 报告"""
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
    
    url_photo = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        # 增加文件存在且不为空的判断
        if photo_path and os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
            with open(photo_path, 'rb') as photo:
                r = requests.post(url_photo, data={'chat_id': MY_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': photo}, timeout=20)
                if r.status_code == 200: return
        
        # 兜底发送纯文本
        requests.post(url_msg, data={'chat_id': MY_CHAT_ID, 'text': caption, 'parse_mode': 'HTML'}, timeout=15)
    except Exception as e:
        print(f"[-] TG 发送环节异常: {e}", file=sys.stderr)

def run_test():
    print(f"[*] 正在向远程视觉工厂发起穿透请求...", file=sys.stderr)
    
    # --- 核心优化点：强制拉开时差，解决 No reCAPTCHA clients exist ---
    payload = {
        "url": TARGET_URL,
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "cookies": [],
        # 1. 触发点击蓝色 Renew server 按钮
        "pre_click": "text='Renew server'", 
        # 2. 【核心修复】将等待时间猛增至 12 秒
        # 确保 Google reCAPTCHA 客户端在内存中完全建立，彻底消灭 "No clients exist" 报错
        "wait_before_captcha": 12, 
        "wait_after_click": 5
    }
    
    start_time = time.time()
    try:
        # Actions 超时时间增加到 180s
        response = requests.post(ZEABUR_AI_URL, json=payload, timeout=180)
        elapsed = f"{time.time() - start_time:.2f}s"
        
        photo_file = "factory_live_shot.png"
        if os.path.exists(photo_file): os.remove(photo_file) # 先清理旧图
        
        has_photo = False

        if response.status_code == 200:
            res_data = response.json()
            
            # --- 关键：只要 JSON 里有图，无论成败先存图 ---
            if res_data.get("screenshot"):
                try:
                    with open(photo_file, "wb") as f:
                        f.write(base64.b64decode(res_data.get("screenshot")))
                    has_photo = True
                except: pass

            if res_data.get("success"):
                token = res_data.get("token")
                print(f"[+ SUCCESS] 穿透成功！", file=sys.stderr)
                send_tg_report_with_photo("穿透成功 ✅", elapsed, photo_file if has_photo else None, token)
                return True
            else:
                error_msg = res_data.get("error", "未知错误")
                print(f"[-] 穿透失败: {error_msg}", file=sys.stderr)
                # 即使失败也带图发送给 TG，让你看清现场
                send_tg_report_with_photo(f"穿透失败 ❌ ({error_msg[:100]})", elapsed, photo_file if has_photo else None)
        else:
            print(f"[-] 服务器响应异常: {response.status_code}", file=sys.stderr)
            send_tg_report_with_photo(f"服务器响应异常 ⚠️ ({response.status_code})", elapsed, None)
            
    except Exception as e:
        print(f"[-] 请求流程崩溃: {e}", file=sys.stderr)
        send_tg_report_with_photo("请求流程崩溃 ⚠️", f"{time.time()-start_time:.2f}s", None)
    
    return False

if __name__ == "__main__":
    if run_test():
        print("[*] 测试流程圆满结束。")
    else:
        sys.exit(1)
