"""Make the comparison plates from an earlier bake or the browser acceptance captures."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size):
    return ImageFont.load_default(size=size)


def comparison(before, after, out):
    columns = [("OAK / BRACING","wooden_crate","idle"), ("CEDAR / HINGE","treasure_chest","open"),
               ("STONE / VEIN","boulder","idle"), ("ASHLAR / CUT","stone_pillar","idle")]
    image = Image.new("RGB",(660,380),"#f5f1e5")
    pen = ImageDraw.Draw(image)
    pen.text((18,12),"MODEL STUDY   /   SW",font=font(15),fill="#2d4941")
    for index,(label,name,state) in enumerate(columns):
        x = 84 + index*144
        pen.text((x,44),label,font=font(12),fill="#43584a")
        for row,folder in enumerate((before,after)):
            metadata = folder/name/("metadata.json" if state=="idle" else state+".json")
            if not metadata.exists():
                raise FileNotFoundError(metadata)
            im = Image.open(folder/name/(state+".png")).convert("RGBA")
            c = im.height
            sprite = im.crop((c,0,2*c,c))
            sprite = sprite.crop(sprite.getbbox())
            sprite = sprite.resize((sprite.width*2,sprite.height*2),Image.Resampling.NEAREST)
            floor = 209 + row*151
            image.paste(sprite,(x+(128-sprite.width)//2,floor-sprite.height),sprite)
            pen.line((x,floor+1,x+128,floor+1),fill="#c4c4b4")
    pen.text((12,132),"FIRST",font=font(13),fill="#526459")
    pen.text((12,279),"FINAL",font=font(13),fill="#526459")
    image.save(out/"comparison.png")


def field(captures, out):
    image = Image.new("RGB",(612,344),"#f5f1e5")
    pen = ImageDraw.Draw(image)
    image.paste(Image.open(captures/"lab-size.png").crop((0,27,592,151)),(10,31))
    pen.text((16,8),"GUILDWARD   /   SPRITESTACK AT NATIVE SCALE",font=font(13),fill="#2d4941")
    for col,projection in enumerate(("lab","game")):
        x = 10 + col*300
        pen.text((x+5,170),"24 DEG  /  1.50 PX PER UNIT" if col==0 else "GAME GRID  /  32 x 16 PX",font=font(12),fill="#43584a")
        # Both scenes come directly from the browser at 1 CSS pixel per PNG pixel.
        crate=Image.open(captures/(projection+"-crate.png")).crop((335,22,448,139))
        bridge=Image.open(captures/(projection+"-bridge.png")).crop((210,22,370,139))
        image.paste(crate,(x,196)); image.paste(bridge,(x+113,196))
        pen.text((x+12,316),"2 CRATES",font=font(11),fill="#43584a")
        pen.text((x+132,316),"3 BEAMS",font=font(11),fill="#43584a")
    image.save(out/"field-study.png")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before",type=Path)
    p.add_argument("--after",type=Path,default=Path("docs/assets"))
    p.add_argument("--captures",type=Path)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(exist_ok=True,parents=True)
    if args.before:
        comparison(args.before,args.after,args.out)
    if args.captures:
        field(args.captures,args.out)
