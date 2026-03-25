import sys
import os
import asyncio
import base64
import time
import httpx
import datetime
from playwright.async_api import async_playwright

# --- 核心环境变量 (Actions Secrets) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")
ZEABUR_AI_URL = os.environ.get("ZEABUR_AI_URL") # 你的镜像 /bypass 接口
HOSTUUID = os.environ.get("HOSTUUID")

TARGET_URL = f"https://host2play.gratis/server/renew?i={HOSTUUID}"

async def send_tg_report(status_text, elapsed, photo_path, token=""):
    """图文一体化 TG 报告"""
    beijing_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    display_token = (token[:20] + "...") if token else "无"
    
    caption = (
        f"🛠️ <b>视觉工厂 - 穿透实况报告</b>\n"
        f"————————————————————\n"
        f"👤 <b>UUID:</b> <code>{HOSTUUID[-12:]}</code>\n"
        f"🛰️ <b>状态:</b> {status_text}\n"
        f"⏱️ <b>总计耗时:</b> {elapsed}\n"
        f"🔑 <b>Token摘要:</b> <code>{display_token}</code>\n"
        f"🕒 <b>北京时间:</b> {beijing_time}\n"
        f"————————————————————"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        async with httpx.AsyncClient() as client:
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as img:
                    await client.post(url, data={'chat_id': MY_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}, files={'photo': img}, timeout=20)
            else:
                msg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                await client.post(msg_url, data={'chat_id': MY_CHAT_ID, 'text': caption, 'parse_mode': 'HTML'}, timeout=15)
    except Exception as e:
        print(f"[-] TG 发送异常: {e}")

async def run_workflow():
    start_time = time.time()
    print(f"[*] Actions 本地启动浏览器...", file=sys.stderr)
    
    async with async_playwright() as p:
        # 1. 本地前置操作：点击蓝色按钮以开启人机
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            print(f"[*] 正在点击 Renew server 按钮...", file=sys.stderr)
            
            # 点击页面中心蓝色按钮
            await page.click("button:has-text('Renew server')")
            # 给 5-8 秒让 reCAPTCHA 框架加载
            await asyncio.sleep(8) 

            # 2. 调用镜像：只负责过人机
            print(f"[*] 呼叫远程镜像进行 AI 识图接力...", file=sys.stderr)
            
            # 这里的 payload 只传 URL 和当前的 Cookies 状态
            payload = {
                "url": TARGET_URL,
                "cookies": await context.cookies(),
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "wait_before_captcha": 5 # 镜像内部点勾选框后的等待
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(ZEABUR_AI_URL, json=payload, timeout=150)
                res_data = response.json()
                
                if res_data.get("success"):
                    token = res_data.get("token")
                    print(f"[+ SUCCESS] 镜像已拿回 Token！长度: {len(token)}", file=sys.stderr)
                    
                    # 3. Actions 本地：注入 Token 并完成最后的续期过程
                    await page.evaluate(f"document.querySelector('#g-recaptcha-response').value = '{token}'")
                    
                    # 这里模仿你原本续期成功的判断（比如页面刷新或弹出成功提示）
                    await asyncio.sleep(3)
                    final_shot = "final_success.png"
                    await page.screenshot(path=final_shot)
                    
                    elapsed = f"{time.time() - start_time:.2f}s"
                    await send_tg_report("续期成功 ✅", elapsed, final_shot, token)
                    return True
                else:
                    error_msg = res_data.get("error", "镜像未返回有效结果")
                    print(f"[-] 镜像解析失败: {error_msg}", file=sys.stderr)
                    error_shot = "error_shot.png"
                    await page.screenshot(path=error_shot)
                    await send_tg_report(f"续期失败 ❌ ({error_msg[:50]})", "0s", error_shot)
                    
        except Exception as e:
            print(f"[-] 流程异常: {e}", file=sys.stderr)
        finally:
            await browser.close()
            
    return False

if __name__ == "__main__":
    if not asyncio.run(run_workflow()):
        sys.exit(1)
