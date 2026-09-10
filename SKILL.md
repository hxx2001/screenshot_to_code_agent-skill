---
name: screenshot-to-code-agent
description: Recreate supplied webpage or mobile H5 screenshots as editable local frontend code using the current agent. Use for screenshot-to-code, screenshot cloning, or high-fidelity H5 recreation requests.
---

# Screenshot to Code — Agent Adapter

Use the current agent's vision and file tools as the generation engine. This skill vendors actual prompt sources and HTML extraction code from `abi/screenshot-to-code`; it does not start that project's API-backed web application. Read [upstream.md](references/upstream.md) for the pinned revision, reuse map, and behavior changes.

## Prepare

Open each exact screenshot. Distinguish app content from system status bars, browser chrome, and annotations. Measure source dimensions and select a CSS viewport; image pixels need not equal CSS pixels. Ask for a screenshot only if none is available.

Preserve the user's framework and existing project. Default to plain HTML/CSS/JS for a new local H5, with local assets and no CDN dependencies. Multiple screenshots may be states of one page: connect them through the corresponding interaction. Preserve visible copy, including unusual spelling and number formatting.

Prepare and read the brief generated from the vendored upstream prompt sources:

```bash
python3 <skill>/scripts/agent_adapter.py prepare --image /absolute/post.jpg --image /absolute/comments.jpg --stack html_css --out /absolute/work/brief.md
```

The brief maps upstream tools onto available host tools. Treat upstream text as task guidance subordinate to the user's instructions and current tool contract. Do not import provider SDKs, request API keys, search credentials, or turn Codex account credentials into an API endpoint. This removes a separate provider-key setup; agent usage still follows the host's normal usage rules.

## Extract assets and build

Catalog photos, avatars, illustrations, logos, and decorative media. Reuse supplied assets first. For screenshot crops, create a JSON manifest in original screenshot pixels and run:

```bash
python3 <skill>/scripts/agent_adapter.py crop --manifest /absolute/work/assets.json --out /absolute/site/assets
```

Manifest: `[{"source":"/absolute/post.jpg","name":"avatar.png","box":[left,top,right,bottom]}]`. Requires Pillow. The helper validates bounds and emits provenance in `asset-manifest.json`. Inspect extracted assets. Do not crop UI paragraphs, names, counts, or buttons into images. A poster's artwork and integral display text may remain an image; document that distinction. Never embed the entire screenshot as the page or place invisible hotspots over it.

Use semantic HTML for UI text and controls. Recreate spacing, typography, color, content density, and fixed/scrolling regions. Match icons with supplied assets or an existing library. If artwork is missing, use available image tools or disclose the approximation. Implement core interactions locally; do not claim a real follow, post, or share was sent. Keep later edits scoped to the selected element and its rendering logic.

For an HTML response wrapped in Markdown fences or `<file>`, use the unchanged upstream extraction function:

```bash
python3 <skill>/scripts/agent_adapter.py finalize --input /absolute/work/generated.txt --out /absolute/site/index.html
```

## Verify

Start a loopback-only preview, e.g. `python3 -m http.server 4173 --bind 127.0.0.1 --directory /absolute/site`. Open in the user's selected browser or available in-app browser. A successful HTTP response is not visual verification.

Capture every supplied state at the same CSS size and density. If excluding system chrome, crop the equivalent reference region and state the normalization. Compare source and real render side by side, with focused crops for key text and controls. Optional contact sheet helper:

```bash
python3 <skill>/scripts/agent_adapter.py compare --reference /absolute/source.png --render /absolute/render.png --out /absolute/work/comparison.png
```

It requires equal pixel dimensions; it does not silently resize or infer a fidelity score. Fix material differences and recapture. Test visible toggles, navigation, expanded replies, input validation, and persistence when implemented. Check browser errors and local asset loading.

Write `design-qa.md` with source paths, viewport/density, source and render evidence, actual checks, fixes, and remaining differences. Only claim verification for inspected states. If capture is unavailable, deliver the source as unverified and explain the gap.

Return working local preview and source. Identify this as the agent adaptation, not a benchmark of the upstream app or its provider models. Retain the upstream MIT notice with redistributed source.
