import sys
import os
import time
import json
import requests
import base64
import datetime
from seleniumbase import SB

# --- 核心环境变量 (Actions Secrets) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")
ZEABUR_AI_URL = os.environ.get("ZEABUR_AI_URL") # 镜像 /bypass 接口
HOSTUUID = os.environ.get("HOSTUUID")

TARGET_URL = f"https://host2play.gratis/server/renew?i={HOSTUUID}"

def smart_ad_remover(sb):
    """【检测广告并清除】物理抹除遮挡层"""
    sb.execute_script("""
        var selectors = ['div[role="dialog"]', '.fc-dialog-container', '.fc-monetization-dialog-container', '.fc-dialog-overlay', 'div[class*="fc-"]', 'ins.adsbygoogle', 'div[id*="google_ads"]'];
        selectors.forEach(function(s) {
            document.querySelectorAll(s).forEach(el => el.remove());
        });
        if (document.body) {
            document.body.style.setProperty('overflow', 'auto', 'important');
        }
    """)

def send_ui_report(account, expiry_date, photo_path, status_text="续期成功 ✅"):
    """【合并版精美报告】图文一体"""
    beijing_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    report_html = (
        f"✅ <b>Host2Play-自动续期报告by-Baico</b>\n"
        f"————————————————————\n"
        f"👤 <b>UUID:</b> <code>{account[-12:]}</code>\n"
        f"🛰️ <b>状态:</b> {status_text}\n"
        f"📅 <b>过期时间/状态:</b> {expiry_date}\n"
        f"🕒 <b>北京时间:</b> {beijing_time}\n"
        f"————————————————————"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                requests.post(url, data={
                    'chat_id': MY_CHAT_ID, 
                    'caption': report_html, 
                    'parse_mode': 'HTML'
                }, files={'photo': photo}, timeout=15)
    except: pass

def run_workflow(sb):
    """
    【精修判定闭环版】逻辑 - 识图部分接力给镜像
    """
    try:
        sb.open(TARGET_URL)
        time.sleep(5)
        smart_ad_remover(sb)
        
        # 1. 点击初始的 Renew server 按钮进入弹窗
        sb.click('button:contains("Renew server")')
        time.sleep(3)
        
        success_flag = False
        for attempt in range(6): 
            # 2. 点击勾选框 iframe
            iframe_check = 'iframe[title="reCAPTCHA"]'
            sb.wait_for_element_present(iframe_check, timeout=20)
            sb.switch_to_frame(iframe_check)
            
            if not sb.is_element_visible('.recaptcha-checkbox-checked'):
                sb.click('.recaptcha-checkbox-border')
            
            sb.switch_to_default_content()
            time.sleep(5)

            # --- 3. 识图接力：如果弹出了验证挑战，呼叫镜像 ---
            challenge_selector = 'iframe[src*="api2/bframe"]'
            if sb.is_element_visible(challenge_selector):
                print(f"[*] 发现识图挑战，呼叫远程镜像接力...", file=sys.stderr)
                payload = {
                    "url": TARGET_URL,
                    "cookies": sb.get_cookies(), # 共享 Session
                    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "wait_before_captcha": 5
                }
                try:
                    # 镜像去解验证码，解完后本地页面的 Token 会同步刷新
                    requests.post(ZEABUR_AI_URL, json=payload, timeout=120)
                except: pass

            # --- 4. 物理真值判定 (你的核心逻辑) ---
            time.sleep(6) 
            recaptcha_token = sb.execute_script("return document.querySelector('#g-recaptcha-response').value;")
            
            sb.switch_to_frame(iframe_check)
            is_checked = sb.get_attribute('#recaptcha-anchor', 'aria-checked') == 'true'
            is_tick_visible = sb.is_element_visible('.recaptcha-checkbox-checkmark')
            sb.switch_to_default_content()

            if recaptcha_token and len(recaptcha_token) > 50 and is_checked and is_tick_visible:
                # 勾选框变绿且拿到 Token，点击 Renew 提交
                renew_btn = 'button.swal2-confirm.swal2-styled'
                if sb.is_element_visible(renew_btn):
                    sb.click(renew_btn)
                    print(f"[+] 验证成功，接收 Token ({len(recaptcha_token)})，提交续期！", file=sys.stderr)
                    time.sleep(10)
                    success_flag = True
                    break 
            else:
                print(f"[!] 第 {attempt + 1} 轮验证未完全通过，刷新重试...", file=sys.stderr)
                sb.refresh()
                time.sleep(5)
                smart_ad_remover(sb)
                sb.click('button:contains("Renew server")')
                time.sleep(3)

        if not success_flag: return False
        
        # 4. 截图并回传最终结果
        final_shot = "final_success.png"
        sb.save_screenshot(final_shot)
        expiry = sb.get_text('#expireDate') if sb.is_element_visible('#expireDate') else "已提交"
        
        send_ui_report(TARGET_URL, expiry, final_shot)
        return True
        
    except Exception as e:
        print(f"[-] 流程异常: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # 使用你指定的 SeleniumBase 启动方式
    with SB(uc=True, test=True, locale="en") as sb:
        if not run_workflow(sb):
            sys.exit(1)
