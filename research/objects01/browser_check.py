"""Optional browser acceptance run (Playwright Python and a local Chrome/Edge)."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="HTTP base URL serving docs/")
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    url = args.url.rstrip("/") + "/"
    run_checks = Path(__file__).with_name("gallery_checks.js").read_text(encoding="utf-8")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.browser, headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: errors.append(str(r.status)+" "+r.url) if r.status >= 400 else None)
        page.goto(url+"objects.html")
        assert page.locator(".asset-card").count() == 4
        page.select_option("#project-filter","guildward")
        assert page.locator(".asset-card").count() == 4
        page.goto(url+"projects.html?id=guildward")
        assert page.locator("section").filter(has_text="制作候補").locator(".asset-card").count() == 4
        for name in ("wooden_crate","treasure_chest","boulder","stone_pillar"):
            page.goto(url+"viewer.html?id="+name+"&scale=1&speed=1")
            page.wait_for_function("document.querySelector('#frame').textContent === '1 / 1'")
            print(name, page.evaluate(run_checks, {"id":name}), "canvas cells", flush=True)
        for kind in ("characters","monsters"):
            page.goto(url+kind+".html")
            assert page.locator(".asset-card").count() == (9 if kind == "characters" else 2)
        for entry in [url+"party.html",(ROOT/"docs/party.html").as_uri()]:
            page.goto(entry)
            page.wait_for_function("document.querySelector('#view-state').textContent.includes('4人')")
            assert page.locator("[data-member]").count() == 5
        page.goto(url+"object-study.html")
        page.wait_for_function("document.querySelector('#caption').textContent.includes('4種類')")
        dirs = page.locator("#facing option").all_text_contents()
        for projection in ("lab","game"):
            page.select_option("#projection",projection)
            for scene in ("size","crate","chest","roll","bridge"):
                page.click(f"[data-scene={scene}]")
                if scene == "chest":
                    page.wait_for_function("document.querySelector('#pose').textContent === 'OPEN'")
                if scene == "bridge":
                    page.wait_for_function("document.querySelector('#pose').textContent.startsWith('BEAM')")
                    for n in ("1","2","3"):
                        page.select_option("#length",n)
                        assert page.inner_text("#pose") == "BEAM × "+n
                for direction in dirs:
                    page.select_option("#facing",direction)
                    assert direction in page.locator("#study").get_attribute("aria-label")
                page.select_option("#facing","SW")
                page.locator("#study").screenshot(path=args.out/(projection+"-"+scene+".png"))
            page.click("[data-scene=size]")
        assert not errors, errors
        print("PASS", browser.version, "5 scenes x 2 projections x 8 directions; party HTTP/file")
        browser.close()


if __name__ == "__main__":
    main()
