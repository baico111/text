import sys
import os
import time
import json
import requests
import asyncio
import re
import datetime
import base64
from seleniumbase import SB

# --- 核心环境变量 ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")
# 这里填你 Zeabur 的地址，例如 https://cfps.zeabur.app/bypass
ZEABUR_AI_URL = os.environ.get("ZEABUR_AI_URL") 
HOSTUUID = os.environ.get("HOSTUUID")

if not HOSTUUID or not ZEABUR_AI_URL:
    print("[-] 错误：缺少 HOSTUUID 或 ZEABUR_AI_URL", file=sys.stderr)
    sys.exit(1)

HOST2PLAY_URL = f"https://host2play.gratis/server/renew?i={HOSTUUID}"

async def solve_via_zeabur(image_path, task_text):
    """【核心】调用你刚才在 Zeabur 部署的视觉工厂"""
    if not os.path.exists(image_path): return None
    
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    # 构造请求，匹配你镜像里 main.py 的 /bypass 接口
    payload = {
        "url": HOST2PLAY_URL,
        "image_b64": img_b64,
        "site": "Zeabur_Test_Factory",
        "task": task_text
    }
    
    try:
        # 增加超时限制，给三模型并发留足时间
        r = requests.post(ZEABUR_AI_URL, json=payload, timeout=45)
        if r.status_code == 200:
            res = r.json()
            # 你的镜像返回的是共识 X, Y 坐标 (0-100)
            return res.get("x"), res.get("y")
    except Exception as e:
        print(f"[-] 调用 Zeabur 视觉工厂失败: {e}", file=sys.stderr)
    return None

def send_tg_report(expiry_date, photo_path):
    """精美 TG 报告，只发一条图文消息"""
    beijing_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    report_html = (
        f"🚀 <b>视觉工厂测试 - 续期报告</b>\n"
        f"————————————————————\n"
        f"👤 <b>UUID:</b> <code>{HOSTUUID[-12:]}</code>\n"
        f"🛰️ <b>状态:</b> 镜像对接成功 ✅\n"
        f"📅 <b>过期时间:</b> {expiry_date}\n"
        f"🕒 <b>执行时间:</b> {beijing_time}\n"
        f"————————————————————"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': MY_CHAT_ID, 'caption': report_html, 'parse_mode': 'HTML'}, files={'photo': photo}, timeout=15)
    except: pass

def run_workflow(sb):
    try:
        sb.open(HOST2PLAY_URL)
        time.sleep(5)
        
        # 1. 唤起弹窗
        sb.click('button:contains("Renew server")')
        time.sleep(3)
        
        # 2. 点击勾选框
        iframe_check = 'iframe[title="reCAPTCHA"]'
        sb.wait_for_element_present(iframe_check, timeout=15)
        sb.switch_to_frame(iframe_check)
        sb.click('.recaptcha-checkbox-border')
        sb.switch_to_default_content()
        time.sleep(4)

        # 3. 识图闭环
        challenge_selector = 'iframe[src*="api2/bframe"]'
        if sb.is_element_visible(challenge_selector):
            sb.switch_to_frame(challenge_selector)
            
            # 截图验证码
            captcha_path = "test_captcha.png"
            sb.save_screenshot(captcha_path)
            task_text = sb.get_text('div.rc-imageselect-desc-wrapper').replace('\n', ' ')
            
            # --- 调用 Zeabur 镜像识别 ---
            print(f"[*] 正在将验证码投喂给视觉工厂...", file=sys.stderr)
            coords = asyncio.run(solve_via_zeabur(captcha_path, task_text))
            
            if coords:
                x_pct, y_pct = coords
                print(f"[+] 工厂返回共识坐标: {x_pct}, {y_pct}", file=sys.stderr)
                # 使用 offset 点击，将 0-100 转换为像素
                sb.click_with_offset('body', x_pct, y_pct)
                time.sleep(1)
                sb.click('#recaptcha-verify-button')
            
            sb.switch_to_default_content()
            time.sleep(5)

        # 4. 提交并报告
        confirm_btn = 'button.swal2-confirm'
        if sb.is_element_visible(confirm_btn):
            sb.click(confirm_btn)
            time.sleep(5)
            final_shot = "final_success.png"
            sb.save_screenshot(final_shot)
            expiry = sb.get_text('#expireDate') if sb.is_element_visible('#expireDate') else "测试完成"
            send_tg_report(expiry, final_shot)
            return True
        return False
    except Exception as e:
        print(f"[-] 流程异常: {e}", file=sys.stderr)
        return False

def main():
    # 纯净启动，不带任何额外的 hook
    with SB(uc=True, test=True, locale="en") as sb:
        if run_workflow(sb):
            print("[+ SUCCESS] 视觉工厂测试任务圆满成功！", file=sys.stderr)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
