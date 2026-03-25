import sys
import os
import time
import json
import requests
import base64
import datetime

# --- 核心环境变量 (从 GitHub Secrets 读取) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")
# 对应镜像的 /bypass 接口
ZEABUR_AI_URL = os.environ.get("ZEABUR_AI_URL") 
HOSTUUID = os.environ.get("HOSTUUID")

if not HOSTUUID or not ZEABUR_AI_URL:
    print("[-] 错误：环境变量配置不全", file=sys.stderr)
    sys.exit(1)

# 目标地址
TARGET_URL = f"https://host2play.gratis/server/renew?i={HOSTUUID}"

def send_tg_report(status_text, elapsed, token=""):
    """发送中文测试报告"""
    beijing_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    # 如果 Token 太长，截取前 20 位展示
    display_token = (token[:20] + "...") if token else "无"
    
    report_html = (
        f"🛠️ <b>视觉工厂 - 通用穿透测试</b>\n"
        f"————————————————————\n"
        f"🛰️ <b>测试状态:</b> {status_text}\n"
        f"⏱️ <b>耗时:</b> {elapsed}\n"
        f"🔑 <b>Token摘要:</b> <code>{display_token}</code>\n"
        f"🕒 <b>北京时间:</b> {beijing_time}\n"
        f"————————————————————"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': MY_CHAT_ID, 'text': report_html, 'parse_mode': 'HTML'}, timeout=15)
    except: pass

def run_test():
    print(f"[*] 正在向视觉工厂发送穿透请求: {ZEABUR_AI_URL}", file=sys.stderr)
    
    # 构造投喂数据
    payload = {
        "url": TARGET_URL,
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "cookies": [] # 如果有登录后的 Cookies 可以放在这里
    }
    
    start_time = time.time()
    try:
        # 视觉工厂在后端会启动浏览器，处理所有 Iframe，模拟点击，最后返回 Token
        # 设置 120 秒超时，因为人机验证可能需要识别多轮
        response = requests.post(ZEABUR_AI_URL, json=payload, timeout=120)
        elapsed = f"{time.time() - start_time:.2f}s"
        
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("success"):
                token = res_data.get("token")
                print(f"[+ SUCCESS] 穿透成功！拿到 Token: {token[:30]}...", file=sys.stderr)
                send_tg_report("穿透成功 ✅", elapsed, token)
                return True
            else:
                error_msg = res_data.get("error", "未知错误")
                print(f"[-] 穿透失败: {error_msg}", file=sys.stderr)
                send_tg_report(f"穿透失败 ❌ ({error_msg})", elapsed)
        else:
            print(f"[-] 服务器响应异常: {response.status_code}", file=sys.stderr)
            send_tg_report(f"服务器异常 ⚠️ ({response.status_code})", elapsed)
            
    except Exception as e:
        elapsed = f"{time.time() - start_time:.2f}s"
        print(f"[-] 请求超时或崩溃: {e}", file=sys.stderr)
        send_tg_report("请求超时/崩溃 ⚠️", elapsed)
    
    return False

if __name__ == "__main__":
    if run_test():
        print("[*] 测试流程结束。")
    else:
        sys.exit(1)
