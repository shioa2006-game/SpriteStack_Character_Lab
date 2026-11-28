"""Photograph the fixture dioramas and exercise every delivered view in Chrome."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import IDS


def main(url, browser_path, out):
    out.mkdir(parents=True,exist_ok=False)
    check_viewer=Path(__file__).resolve().parents[1].joinpath("objects01/gallery_checks.js").read_text(encoding="utf-8")
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=browser_path,headless=True)
        page=browser.new_page(viewport={"width":1240,"height":950},device_scale_factor=1)
        errors=[]
        page.on("pageerror",lambda e: errors.append(str(e)))
        page.on("response",lambda r:errors.append(r.url) if r.status>=400 else None)
        page.goto(url+"/chapter1.html")
        page.wait_for_function("document.querySelector('#status').textContent.includes('仮配置')")
        assert page.locator(".fixture").count()==6
        scenes=page.locator("#scenes")
        scenes.screenshot(path=out/"installation.png")
        for cam in ("game","lab"):
            page.select_option("#camera",cam)
            for d in page.locator("#yaw option").all_text_contents():
                page.select_option("#yaw",d)
                assert d in page.inner_text("#status")
                for id in IDS:
                    page.select_option("#inspect",id)
                    card=page.locator("figure").filter(has=page.locator('a[href="viewer.html?id='+id+'"]'))
                    choice=card.locator("select").first
                    if card.locator("select").count():
                        samples=[]
                        for state in choice.locator("option").evaluate_all("opts=>opts.map(o=>o.value)"):
                            choice.select_option(state)
                            assert page.inner_text("#coordinates")
                            if d=="SW":
                                samples.append(card.locator("canvas").evaluate("c=>c.toDataURL()"))
                        assert len(samples)==len(set(samples)),id+" state change in scene"
                page.check("#pins");page.uncheck("#pins")
            page.select_option("#yaw","SW")
            page.select_option("#zoom","1")
            scenes.screenshot(path=out/(cam+"-1x.png"))
            page.select_option("#zoom","2")
            scenes.screenshot(path=out/(cam+"-2x.png"))
        page.select_option("#camera","game")
        page.select_option("[aria-label='灯の組み合わせ']","11")
        page.select_option("[aria-label='人物の位置']","back")
        scenes.screenshot(path=out/"activated.png")
        cells=0
        for id in IDS:
            page.goto(url+"/viewer.html?id="+id+"&scale=1&speed=1")
            page.wait_for_function("document.querySelector('#frame').textContent==='1 / 1'")
            cells+=page.evaluate(check_viewer,{"id":id})
        assert not errors,errors
        print("PASS",browser.version,cells,"viewer cells; six installations in 2 cameras and 8 directions")
        browser.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",required=True)
    parser.add_argument("--browser",required=True)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    main(args.url.rstrip("/"),args.browser,args.out)
