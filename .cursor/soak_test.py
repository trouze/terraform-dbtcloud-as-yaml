#!/usr/bin/env python3
"""Stability soak: 8 cycles of /match <-> /fetch_target with snapshots and harmless clicks."""

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
CYCLES = 8
WAIT_MS = 2000
NAV_RETRIES = 2

# Keywords to flag in console/errors
FLAG_PATTERNS = [
    "websocket",
    "timeout",
    "reconnect",
    "closed",
    "slot",
    "client",
    "deleted",
]


def main():
    console_logs = []
    page_errors = []
    crashes = []
    cycle_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_console(msg):
            console_logs.append({"type": msg.type, "text": msg.text})

        def on_page_error(err):
            page_errors.append(str(err))

        page.on("console", on_console)
        page.on("pageerror", on_page_error)

        for i in range(CYCLES):
            # --- /match ---
            try:
                for attempt in range(NAV_RETRIES + 1):
                    try:
                        page.goto(f"{BASE}/match", wait_until="load", timeout=20000)
                        break
                    except Exception as nav_err:
                        if attempt < NAV_RETRIES and "ERR_ABORTED" in str(nav_err):
                            page.wait_for_timeout(2000)
                            continue
                        raise
                page.wait_for_timeout(WAIT_MS)
                title = page.title()
                body_len = len(page.locator("body").inner_text())
                # Click harmless control: "Go to Scope" or first edit button
                scope_btn = page.get_by_role("button", name="Go to Scope")
                edit_btn = page.locator("button").filter(has_text="edit").first
                if scope_btn.count() > 0:
                    scope_btn.click(timeout=3000)
                    page.wait_for_timeout(1500)  # let navigation settle
                elif edit_btn.count() > 0:
                    edit_btn.click(timeout=3000)
                    page.wait_for_timeout(500)
                    page.keyboard.press("Escape")  # dismiss dialog if any
                cycle_results.append(("match", True, title, body_len))
            except Exception as e:
                cycle_results.append(("match", False, str(e), 0))
                crashes.append(("match", str(e)))

            # --- /fetch_target ---
            try:
                for attempt in range(NAV_RETRIES + 1):
                    try:
                        page.goto(f"{BASE}/fetch_target", wait_until="load", timeout=20000)
                        break
                    except Exception as nav_err:
                        if attempt < NAV_RETRIES and "ERR_ABORTED" in str(nav_err):
                            page.wait_for_timeout(2000)
                            continue
                        raise
                page.wait_for_timeout(WAIT_MS)
                title = page.title()
                body_len = len(page.locator("body").inner_text())
                # Click harmless control: Load .env or edit
                load_btn = page.get_by_role("button", name="Load .env")
                if load_btn.count() == 0:
                    load_btn = page.locator("button").filter(has_text="Load default .env").first
                edit_btn = page.locator("button").filter(has_text="edit").first
                if load_btn.count() > 0:
                    load_btn.click(timeout=3000)
                    page.wait_for_timeout(800)
                    page.keyboard.press("Escape")  # dismiss dialog if any
                elif edit_btn.count() > 0:
                    edit_btn.click(timeout=3000)
                    page.wait_for_timeout(500)
                    page.keyboard.press("Escape")
                cycle_results.append(("fetch_target", True, title, body_len))
            except Exception as e:
                cycle_results.append(("fetch_target", False, str(e), 0))
                crashes.append(("fetch_target", str(e)))

        browser.close()

    # Analyze logs for flagged patterns
    flagged = []
    for log in console_logs + [{"type": "error", "text": e} for e in page_errors]:
        text = (log.get("text") or "").lower()
        for pat in FLAG_PATTERNS:
            if pat in text:
                flagged.append({"pattern": pat, "type": log.get("type", "pageerror"), "text": text[:300]})
                break

    # Report
    print("=" * 60)
    print("STABILITY SOAK REPORT")
    print("=" * 60)
    print(f"Cycles: {CYCLES} | Page loads: {CYCLES * 2}")
    print()
    passed = all(r[1] for r in cycle_results)
    print("PASS" if passed and not crashes and not flagged else "FAIL")
    print()
    print("Cycle results:")
    for r in cycle_results:
        status = "OK" if r[1] else "FAIL"
        print(f"  {r[0]}: {status} (title/body: {r[2][:40]}... / {r[3]} chars)")
    if crashes:
        print("\nCrashes:")
        for page_name, err in crashes:
            print(f"  {page_name}: {err[:200]}")
    if flagged:
        print("\nFlagged console/errors (websocket, slot, deleted, etc.):")
        for f in flagged[:20]:
            print(f"  [{f['pattern']}] {f['type']}: {f['text'][:150]}...")
    print(f"\nTotal console messages: {len(console_logs)}")
    print(f"Total page errors: {len(page_errors)}")
    if page_errors:
        for e in page_errors[:5]:
            print(f"  {e[:200]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
