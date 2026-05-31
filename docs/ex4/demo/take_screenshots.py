"""
Playwright screenshot script for the Ex4 Chat UI demo.

Usage (from repo root):
    python3 docs/ex4/demo/take_screenshots.py

Prerequisites:
    - docker compose up -d          (Postgres + API on :8000)
    - npm run dev -- --port 5174    (Vite frontend; requires Node >=20)
    - playwright installed: pip install playwright && playwright install chromium

Screenshots land in docs/ex4/demo/.
"""
import asyncio
from pathlib import Path

OUT = Path(__file__).parent

async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # 1 — Login
        await page.goto("http://localhost:5174/login")
        await page.fill('input[type="email"]', "admin@hellio.com")
        await page.fill('input[type="password"]', "admin123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/candidates**", timeout=5000)
        await page.screenshot(path=str(OUT / "demo_01_candidates.png"))
        print("✓ 01 candidates page")

        # 2 — Chat empty
        await page.click("text=Ask")
        await page.wait_for_url("**/chat**", timeout=3000)
        await page.screenshot(path=str(OUT / "demo_02_chat_empty.png"))
        print("✓ 02 chat empty")

        # 3 — Question typed
        await page.fill('input[placeholder*="positions"]', "how many active candidates are there?")
        await page.screenshot(path=str(OUT / "demo_03_chat_typed.png"))
        print("✓ 03 question typed")

        # 4 — Thinking
        await page.click('button[type="submit"]')
        await page.wait_for_selector("text=Thinking", timeout=3000)
        await page.screenshot(path=str(OUT / "demo_04_thinking.png"))
        print("✓ 04 thinking")

        # 5 — Answered (panel collapsed)
        await page.wait_for_selector("text=What was retrieved", timeout=30000)
        await page.screenshot(path=str(OUT / "demo_05_answered.png"))
        print("✓ 05 answered")

        # 6 — Panel expanded
        await page.click("text=What was retrieved")
        await page.screenshot(path=str(OUT / "demo_06_panel_open.png"))
        print("✓ 06 panel open")

        await browser.close()

asyncio.run(run())
