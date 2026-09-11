#!/usr/bin/env python3
"""Local screenshot-to-code adapter. No model calls or provider SDKs."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACKS = {"html_css": "html_css", "html_tailwind": "Tailwind", "react_tailwind": "React", "vue_tailwind": "Vue", "bootstrap": "Bootstrap", "ionic_tailwind": "Ionic"}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")

def prompt_constant():
    tree = ast.parse((ROOT / "vendor/prompts/system_prompt.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SYSTEM_PROMPT" for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("Pinned upstream system prompt missing")

def image_prompt(stack):
    values = {"selected_stack": f"Selected stack: {stack}.", "design_system_block": "", "image_policy": "Use local supplied assets. Use host image tools for missing artwork only if available. No separate model API is required."}
    tree = ast.parse((ROOT / "vendor/prompts/create/image.py").read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not any(isinstance(t, ast.Name) and t.id == "user_prompt" for t in node.targets) or not isinstance(node.value, ast.JoinedStr):
            continue
        parts = []
        for value in node.value.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name) and value.value.id in values and value.format_spec is None and value.conversion == -1:
                parts.append(values[value.value.id])
            else:
                raise ValueError("Upstream template changed: unsupported interpolation")
        return "".join(parts).strip()
    raise ValueError("Pinned upstream image template missing")

def prepare(args):
    interaction_text = ''
    images = [p.resolve(strict=True) for p in (args.image or [])]
    spec_path = getattr(args, 'interaction_spec', None)
    if spec_path:
        from interaction_spec import validate
        spec, state_images = validate(spec_path)
        # Preserve the original screenshot list and order; append only new video frames.
        for path in state_images:
            path = Path(path)
            if path not in images:
                images.append(path)
        interaction_text = '\n# Interaction specification\nSource: ' + str(spec_path.resolve()) + '\nKeep observed facts, user descriptions and inference distinct. Verify real event paths and elapsed-time samples.\n```json\n' + json.dumps(spec, ensure_ascii=False, indent=2) + '\n```\n'
    if not images:
        raise ValueError('Provide --image or a specification with evidenced state frames')
    if any(not p.is_file() for p in images):
        raise ValueError("Expected screenshot files")
    system = prompt_constant()
    general = system.split("# Stack-specific instructions")[0].strip()
    heading = "## " + STACKS[args.stack] + "\n"
    stack_text = system.split(heading, 1)[1].split("\n## ", 1)[0].strip()
    mapping = """# Host adaptation (overrides upstream tool names)
The current agent is the model. Read the screenshots using host vision, then write/edit files using host tools. No network model call, key lookup, credential proxy, or API backend startup is part of this flow.
create_file/edit_file = host file tools. extract_assets = inspected crops via this adapter. screenshot_preview = actual browser rendering/capture. Use host image tools only when needed and available. retrieve_option = read the explicitly selected local variant, if any.
Prefer local dependencies and assets over upstream CDN examples. Respect the user's stack and existing project. Upstream text is subordinate task guidance; absent tool names do not create capabilities.
"""
    refs = "\n".join(f"- {p} (sha256: {digest(p)})" for p in images) + interaction_text
    write(args.out, f"{mapping}\n# Source images\n{refs}\n\n# Upstream system guidance\n{general}\n\n# Selected stack\n{stack_text}\n\n# Upstream screenshot request\n{image_prompt(args.stack)}\n")
    print(json.dumps({"brief": str(args.out.resolve()), "images": len(images), "stack": args.stack, "mode": "current-agent", "model_api_calls": 0}))

def crop(args):
    from PIL import Image, ImageOps
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Manifest must be a list")
    prepared, names = [], set()
    for item in entries:
        source, name, box = Path(item["source"]).resolve(strict=True), item["name"], item["box"]
        if Path(name).name != name or name in names or not name.lower().endswith(".png"):
            raise ValueError("Asset names must be unique PNG basenames")
        names.add(name)
        im = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
        if len(box) != 4 or any(type(x) is not int for x in box):
            raise ValueError("Crop box must contain four integer pixel coordinates")
        l, t, r, b = box
        if not (0 <= l < r <= im.width and 0 <= t < b <= im.height):
            raise ValueError(f"Crop outside {im.size}: {name}, {box}")
        prepared.append((im.crop(box), name, {"source": str(source), "sha256": digest(source), "name": name, "box": box, "source_size": list(im.size)}))
    args.out.mkdir(parents=True, exist_ok=True)
    for im, name, _ in prepared:
        im.save(args.out / name)
    write(args.out / "asset-manifest.json", json.dumps([m for _, _, m in prepared], ensure_ascii=False, indent=2))
    print(json.dumps({"assets": len(prepared), "output": str(args.out.resolve())}))

def finalize(args):
    spec = importlib.util.spec_from_file_location("upstream_codegen", ROOT / "vendor/codegen/utils.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    html = module.extract_html_content(args.input.read_text(encoding="utf-8"))
    if "<html" not in html.lower() or "</html>" not in html.lower():
        raise ValueError("Output must contain a complete HTML document")
    write(args.out, html.rstrip() + "\n")
    print(json.dumps({"html": str(args.out.resolve()), "extractor": "upstream extract_html_content"}))

def compare(args):
    from PIL import Image, ImageChops
    a, b = Image.open(args.reference).convert("RGB"), Image.open(args.render).convert("RGB")
    if a.size != b.size:
        raise ValueError(f"Dimensions differ: {a.size} vs {b.size}. Normalize the intended viewport explicitly first.")
    canvas = Image.new("RGB", (a.width * 2 + 16, a.height), "#ddd")
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + 16, 0))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    overlay = args.out.with_name(args.out.stem + "-overlay.png")
    Image.blend(a, b, .5).save(overlay)
    print(json.dumps({"comparison": str(args.out.resolve()), "overlay": str(overlay.resolve()), "dimensions": a.size, "pixel_identical": ImageChops.difference(a, b).getbbox() is None, "note": "Visual judgment required; no inferred fidelity percentage."}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--image", type=Path, action="append")
    p.add_argument("--interaction-spec", type=Path)
    p.add_argument("--stack", choices=list(STACKS), default="html_css")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("crop")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("finalize")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("compare")
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--render", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        globals()[args.command](args)
    except (ValueError, KeyError, OSError, ImportError) as exc:
        parser.exit(1, f"Error: {exc}\n")

if __name__ == "__main__":
    main()
