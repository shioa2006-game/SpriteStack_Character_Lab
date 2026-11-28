"""Exercise the scale study in Chromium and capture the native and enlarged research plates."""
import argparse
from base64 import b64decode
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw
from playwright.sync_api import sync_playwright

SCENES = {"scale": "A   |   Party and equipment", "stand": "B   |   Rico and Gard on each platform",
          "steps": "C   |   Ground, crate and two-step ledge", "stack": "D   |   Two-crate stack",
          "rows": "E   |   Eight camera views"}
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


def capture(canvas, path, zoom=1):
    raw = canvas.evaluate("c => c.toDataURL().split(',')[1]")
    native = Image.open(BytesIO(b64decode(raw))).convert("RGB")
    w,h = native.width*zoom, native.height*zoom
    expected = native.resize((w,h),Image.Resampling.NEAREST)
    actual = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
    # CSS can place the element at a fractional page coordinate. Exclude only
    # the outer page pixels included by Chrome's rounded screenshot rectangle.
    for y in range(actual.height-h+1):
        for x in range(actual.width-w+1):
            pixels = actual.crop((x,y,x+w,y+h))
            if ImageChops.difference(expected,pixels).getbbox() is None:
                pixels.save(path)
                return
    raise AssertionError(f"browser pixels differ from nearest-neighbour {zoom}x: {path}")


def plate(out, filename, panels, zoom):
    images = [(Image.open(out / name).convert("RGB"), title) for name, title in panels]
    # Preserve captured pixels; only trim the empty band above the floor scenes.
    cropped = [(im.crop((0, (0 if "rows" in name else 29)*zoom, im.width, im.height)), title)
               for (im, title), (name, _) in zip(images, panels)]
    width = cropped[0][0].width
    result = Image.new("RGB", (width, sum(im.height+22*zoom for im, _ in cropped)), "#f9f8f0")
    top = 0
    for im, title in cropped:
        strip = Image.new("RGB", (width//zoom, 22), "#f9f8f0")
        ImageDraw.Draw(strip).text((10, 4), title, fill="#33483d")
        result.paste(strip.resize((width, 22*zoom), Image.Resampling.NEAREST), (0, top))
        top += 22*zoom
        result.paste(im, (0,top))
        top += im.height
    result.save(out / filename)


def run(page, out):
    canvas = page.locator("#study")
    page.wait_for_function("document.querySelector('#caption').textContent.includes('木箱3案')")
    assert page.locator("#facing option").all_text_contents() == DIRECTIONS
    for mode in ("lab", "game"):
        page.select_option("#projection", mode)
        for scene in [*SCENES, "pillarScale"]:
            page.click(f"[data-scene={scene}]")
            # Drive the same DOM change handlers as the controls for all camera/size choices.
            checks = page.evaluate("""({scene,mode}) => {
              const el=id=>document.getElementById(id);
              function change(id,value) {
                el(id).value=value; el(id).dispatchEvent(new Event('change',{bubbles:true}));
              }
              let count=0;
              const specimens=scene==='pillarScale'?['all']:['14','8','6','all'];
              for (const specimen of specimens) {
                change('specimen',specimen);
                for (const option of el('facing').options) {
                  change('facing',option.value);
                  if (!el('study').getAttribute('aria-label').includes(option.value) ||
                      !el('pose').textContent || el('dimensions').hidden) throw Error(scene);
                  count++;
                }
              }
              change('facing','SW');
              if (mode==='game' && scene!=='pillarScale') {
                el('fit').click();
                if (!el('pose').textContent.includes('個別')) throw Error('fit');
                el('fit').click();
              }
              return count;
            }""", {"scene":scene,"mode":mode})
            assert checks == (8 if scene == "pillarScale" else 32)
            if scene == "steps":
                for position in ("ground","ledge","crate"):
                    page.select_option("#climb", position)
                    capture(canvas,out/f"{mode}-route-{position}.png")
            if scene == "pillarScale":
                for f in page.locator("#tilt option").evaluate_all("opts => opts.map(o=>o.value)"):
                    page.select_option("#tilt",f)
                    assert page.inner_text("#pose") == page.locator("#tilt option:checked").inner_text()
                    if f in ("0","6","8","beam"):
                        capture(canvas,out/f"{mode}-pillar-{f}.png")
            page.check("#marks")
            with_marks = canvas.screenshot()
            page.uncheck("#marks")
            assert canvas.screenshot() != with_marks
            for zoom in (1,2):
                page.select_option("#zoom",str(zoom))
                path = out / f"{mode}-{scene}-{zoom}x.png"
                capture(canvas,path,zoom)
            page.select_option("#zoom","1")
        for zoom in (1,2):
            plate(out, f"{mode}-comparison-{zoom}x.png",
                  [(f"{mode}-{s}-{zoom}x.png", title) for s,title in SCENES.items()],zoom)
    plate(out, "pillar-comparison.png", [(f"lab-pillar-{f}.png", title) for f,title in
          (("0","Upright"),("6","Late fall"),("8","Fallen"),("beam","Three modules and walker"))],1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.browser, headless=True)
        page = browser.new_page(viewport={"width":1440, "height":900},device_scale_factor=1)
        errors = []
        page.on("pageerror",lambda e: errors.append(str(e)))
        page.on("response",lambda r: errors.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        page.goto(args.url.rstrip("/")+"/object-study.html?scene=scale")
        run(page,args.out)
        assert not errors, errors
        print("PASS", browser.version, "6 scenes, both projections, 8 yaws, 3 specimens, anchors, route, poses and 1x/2x")
        browser.close()


if __name__ == "__main__":
    main()
