"""Bring a Greyhound BO3-format rip into the Mod Tools: copy under model_export/<tag>, convert every
xmodel_export to xmodel_bin (export2bin pattern mode), and rewrite the rip's GDTs to point at the bins
with tools-relative paths, writing them to source_data/<tag>_*.gdt."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

TOOLS = Path(r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130")
EXPORT2BIN = TOOLS / "bin" / "export2bin.exe"
BS = chr(92)


def convert(dest):
    # pattern mode is the only one that really converts; "in out" and /piped just LZ4-wrap the text
    for d in sorted({p.parent for p in dest.rglob("*") if p.suffix.lower() == ".xmodel_export"}):
        subprocess.run([str(EXPORT2BIN), "/v", "*.XMODEL_EXPORT"], cwd=d, check=True, capture_output=True)
    exports = [p for p in dest.rglob("*") if p.suffix.lower() == ".xmodel_export"]
    missing = [p for p in exports if not p.with_suffix(".XMODEL_BIN").exists() and not p.with_suffix(".xmodel_bin").exists()]
    return len(exports), missing


def rewrite_gdt(text, rip, dest):
    def path(m):
        value = m.group(2).replace(BS * 2, BS).replace("/", BS)
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                candidate = dest / candidate.relative_to(rip)
            except ValueError:
                return m.group(0)
            # stock: model filenames are relative to model_export, image baseImages to the tools root
            is_model = candidate.suffix.lower() in (".xmodel_export", ".xmodel_bin")
            value = str(candidate.relative_to(TOOLS / "model_export" if is_model else TOOLS))
        value = re.sub(r"\.xmodel_export$", ".xmodel_bin", value, flags=re.I)
        return f'"{m.group(1)}" "{value.replace(BS, BS * 2)}"'
    # every field holding a file path (filename, *Lod, baseImage, lod*File, ...)
    return re.sub(r'"(\w+)" "([^"]*\.(?:xmodel_export|xmodel_bin|png|tif|tiff|tga|dds))"', path, text, flags=re.I)


STOCK_GDT = TOOLS / "model_export" / "t7_props_adia.gdt"
MATERIAL_LINE = re.compile(r'^MATERIAL (\d+) "([^"]+)" "(\w+)" "color:([^"]*)"', re.M)


def stock_entry(name, gdf):
    text = STOCK_GDT.read_text(errors="replace")
    return re.search(rf'\t"{name}" \( "{gdf}" \)\n\t\{{\n.*?\n\t\}}\n', text, re.S).group()


def entry(template, name, fields):
    out = re.sub(r'^\t"[^"]+" \(', f'\t"{name}" (', template, count=1)
    for key, value in fields.items():
        out = re.sub(rf'"{key}" "[^"]*"', lambda _: f'"{key}" "{value}"', out)
    return out


ALPHA = {}  # material -> materialType, from --alpha (the game's own stateBits); empty = guess from the texture


def cutout(png):
    """True when the texture's alpha cuts holes (foliage, fences): >2% of texels below half alpha."""
    from PIL import Image
    im = Image.open(png)
    if im.mode not in ("RGBA", "LA", "P") or im.convert("RGBA").getchannel("A").getextrema()[0] >= 128:
        return False
    hist = im.convert("RGBA").getchannel("A").histogram()
    return sum(hist[:128]) > 0.02 * sum(hist)


def model_gdt(export, tag, base=None):
    """GDT entries (xmodel + materials + colour/normal images) built from one Greyhound XME, whose
    MATERIAL lines are renamed <tag>_<material> in place so BO4 names never collide with stock BO3."""
    text = export.read_text(errors="replace")
    mat_t, col_t, nrm_t = (stock_entry("mtl_p7_sin_bollard_concrete", "material.gdf"),
                           stock_entry("i_mtl_p7_sin_bollard_c", "image.gdf"), stock_entry("i_mtl_p7_sin_bollard_n", "image.gdf"))
    model_t = re.search(r'\t"zombie_wolf" \( "xmodel.gdf" \)\n\t\{\n.*?\n\t\}\n',
                        (TOOLS / "model_export" / "cod7_zombie_characters.gdt").read_text(errors="replace"), re.S).group()
    rel = lambda p: str(p.relative_to(TOOLS)).replace(BS, BS * 2)
    entries, materials = {}, []
    for _, mat, _, color in MATERIAL_LINE.findall(text):
        folder = (base or export.parent) / "_images" / mat
        name = mat if mat.startswith(f"{tag}_") else f"{tag}_{mat}"
        materials.append(name)
        fields = {"colorMap": "", "normalMap": "", "cosinePowerMap": "", "occMap": "", "specColorMap": ""}
        maps = [("colorMap", col_t, (base or export.parent) / color.replace(BS * 2, BS))]
        maps += [("normalMap", nrm_t, p) for p in folder.glob("*_n.png")][:1]
        for key, template, png in maps:
            if png.is_file():
                if TOOLS not in png.parents:  # textures outside the tools tree are pulled in beside the model
                    local = export.parent / "_images" / mat / png.name
                    local.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(png, local)
                    png = local
                image = f"i_{tag}_{re.sub(r'[^a-z0-9_]', '', png.stem.lower())}"
                image_fields = {"baseImage": rel(png)}
                kind = ALPHA.get(mat) if ALPHA else ("lit_alphatest_nocull" if cutout(png) else None)
                if key == "colorMap" and kind:  # BC7 keeps the alpha; alpha-test is two-sided like stock fences
                    image_fields["compressionMethod"] = "compressed high color"
                    fields["materialType"] = kind
                entries[image] = entry(template, image, image_fields)
                fields[key] = image
        entries[name] = entry(mat_t, name, fields)
    text = MATERIAL_LINE.sub(lambda m: f'MATERIAL {m.group(1)} "{m.group(2) if m.group(2).startswith(tag + "_") else tag + "_" + m.group(2)}" "{m.group(3)}" "color:{m.group(4)}"', text)
    export.write_text(text)
    model = re.sub(r"_LOD0$", "", export.stem, flags=re.I)
    bones = int(re.search(r"^NUMBONES (\d+)", text, re.M).group(1))
    bin_path = str(export.with_suffix(".xmodel_bin").relative_to(TOOLS / "model_export")).replace(BS, BS * 2)
    entries[model] = entry(model_t, model, {"filename": bin_path, "type": "rigid" if bones == 1 else "animated",
                                            "mediumLod": "", "lowLod": "", "lowestLod": "", "BulletCollisionLOD": "None",
                                            # the template's LOD distances with no LOD meshes made models vanish past 500u
                                            "highLodDist": "0", "mediumLodDist": "0", "lowLodDist": "0", "lowestLodDist": "0",
                                            "materials": "".join(m + BS + "r" + BS + "n" for m in materials)})
    return model, entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rip", type=Path)
    ap.add_argument("tag")
    ap.add_argument("--models", nargs="*", help="only these model folders (or, for a flat folder, files; none = all); GDT built from the XME")
    ap.add_argument("--models-from", type=Path, help="text file of model names, one per line (avoids the Windows command-line limit)")
    ap.add_argument("--alpha", type=Path, help="alpha_materials.json: alphatest/blend material lists")
    args = ap.parse_args()
    if args.models_from:
        args.models = (args.models or []) + [m for m in args.models_from.read_text().split() if m]
    if args.alpha:
        lists = json.loads(args.alpha.read_text())
        ALPHA.update({m: "lit_alphatest_nocull" for m in lists["alphatest_materials"]})
        ALPHA.update({m: "lit_transparent" for m in lists["blend_materials"]})
    dest = TOOLS / "model_export" / args.tag
    flat = args.models is not None and not (args.rip / "xmodels").is_dir()  # loose <name>.XMODEL_EXPORT files (shell chunks)
    if flat and not args.models:
        args.models = sorted(p.stem for p in args.rip.glob("*.XMODEL_EXPORT"))
    if args.models:
        entries, models = {}, []
        if flat and (args.rip / "_images").is_dir():
            shutil.copytree(args.rip / "_images", dest / "_images", dirs_exist_ok=True)
        for name in args.models:
            if flat:
                source = args.rip / f"{name}.XMODEL_EXPORT"
                name = re.sub(r"_lod0$", "", name.lower())  # gdtdb rejects upper case in asset names
                (dest / "xmodels" / name).mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest / "xmodels" / name / f"{name}_LOD0.XMODEL_EXPORT")
            else:
                shutil.copytree(args.rip / "xmodels" / name, dest / "xmodels" / name, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("*.semodel", "*.mel"))
            for export in (dest / "xmodels" / name).glob("*_LOD0.XMODEL_EXPORT"):
                model, found = model_gdt(export, args.tag, dest if flat else None)
                models.append(model)
                entries.update(found)
        count, missing = convert(dest)
        (TOOLS / "source_data" / f"{args.tag}.gdt").write_text("{\n" + "".join(entries.values()) + "}\n")
        print(f"{count} xmodel_export -> bin ({len(missing)} failed); {len(entries)} GDT entries; zone lines:")
        print("\n".join(f"xmodel,{m}" for m in models))
        return
    shutil.copytree(args.rip, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.gdt", "*.semodel"))
    count, missing = convert(dest)
    gdts = list(args.rip.rglob("*.gdt"))
    for gdt in gdts:
        out = TOOLS / "source_data" / f"{args.tag}_{gdt.stem}.gdt"
        out.write_text(rewrite_gdt(gdt.read_text(errors="replace"), args.rip.resolve(), dest))
    print(f"{count} xmodel_export -> bin ({len(missing)} failed: {[p.name for p in missing[:10]]}); {len(gdts)} GDTs -> source_data")


if __name__ == "__main__":
    main()
