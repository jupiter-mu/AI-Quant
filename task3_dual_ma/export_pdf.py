"""双均线策略看板 → PDF 导出"""
import os, sys
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE, "output", "dual_ma_report.html")
PDF_PATH = os.path.join(BASE, "output", "dual_ma_report.pdf")

abs_path = os.path.abspath(HTML_PATH).replace("\\", "/")
file_url = f"file:///{abs_path}"

print(f"加载: {file_url}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(file_url, wait_until="networkidle", timeout=60000)

    # Wait for Plotly charts to render
    print("等待图表渲染...")
    page.wait_for_timeout(6000)

    # Verify charts loaded
    has_charts = page.evaluate("document.querySelectorAll('.chart-card').length > 0")
    print(f"图表加载: {has_charts}")

    # Scroll to top
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    print("生成 PDF...")
    page.pdf(
        path=PDF_PATH,
        format="A3",
        print_background=True,
        margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
    )

    browser.close()

size_mb = os.path.getsize(PDF_PATH) / 1024 / 1024
print(f"\n完成! 大小: {size_mb:.1f} MB")
print(f"  {PDF_PATH}")
