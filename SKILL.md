---
name: screenshot-to-code-agent
description: Recreate supplied webpage or mobile H5 screenshots as editable local frontend code using the current agent. Use for screenshot-to-code, screenshot cloning, high-fidelity H5 recreation, or extending the same recreation to demonstrated interactions and motion from screen recordings.
---

# Screenshot to Code — Agent Adapter

Use the current agent's vision and file tools as the generation engine. This skill vendors actual prompt sources and HTML extraction code from `abi/screenshot-to-code`; it does not start that project's API-backed web application. Read [upstream.md](references/upstream.md) for the pinned revision, reuse map, and behavior changes.

## Input route

Screenshot recreation is the base workflow below; recording support adds evidence and motion steps without replacing it.

- **Screenshots only:** follow the base workflow. Multiple images remain supported. No video tools or interaction-spec file are required.
- **Recording, with optional screenshots:** also read [video workflow](references/video-workflow.md). Clear screenshots supply stable visual detail; native video frames fill missing states. Keep conflicting versions separate rather than silently mixing layouts. Record observed states and transitions before implementation.

## Prepare

Open each exact screenshot. Distinguish app content from system status bars, browser chrome, and annotations. Measure source dimensions and select a CSS viewport; image pixels need not equal CSS pixels. Ask for a screenshot only if none is available.

Preserve the user's framework and existing project. Default to plain HTML/CSS/JS for a new local H5, with local assets and no CDN dependencies. Multiple screenshots may be states of one page: connect them through the corresponding interaction. Preserve visible copy, including unusual spelling and number formatting.

Prepare and read the brief generated from the vendored upstream prompt sources:

```bash
python3 <skill>/scripts/agent_adapter.py prepare --image /absolute/post.jpg --image /absolute/comments.jpg --stack html_css --out /absolute/work/brief.md
```

For recordings, append `--interaction-spec /absolute/work/interaction-spec.json` to the same command; `--image` remains repeatable and optional only when the specification supplies state frames. Read [interaction specification](references/interaction-spec.md) for that additional input. Read the original screenshot guidance in the generated brief for either route.

The brief maps upstream tools onto available host tools. Treat upstream text as task guidance subordinate to the user's instructions and current tool contract. Do not import provider SDKs, request API keys, search credentials, or turn Codex account credentials into an API endpoint. This removes a separate provider-key setup; agent usage still follows the host's normal usage rules.

## Extract assets and build

Catalog photos, avatars, illustrations, logos, and decorative media. Reuse supplied assets first. For screenshot crops, create a JSON manifest in original screenshot pixels and run:

```bash
python3 <skill>/scripts/agent_adapter.py crop --manifest /absolute/work/assets.json --out /absolute/site/assets
```

Manifest: `[{"source":"/absolute/post.jpg","name":"avatar.png","box":[left,top,right,bottom]}]`. Requires Pillow. The helper validates bounds and emits provenance in `asset-manifest.json`. Inspect extracted assets. Do not crop UI paragraphs, names, counts, or buttons into images. A poster's artwork and integral display text may remain an image; document that distinction. Never embed the entire screenshot as the page or place invisible hotspots over it.

Use semantic HTML for UI text and controls. Recreate spacing, typography, color, content density, and fixed/scrolling regions. Match icons with supplied assets or an existing library. If artwork is missing, use available image tools or disclose the approximation. Implement core interactions locally; do not claim a real follow, post, or share was sent. Keep later edits scoped to the selected element and its rendering logic.

Apply [page fidelity](references/page-fidelity.md) to screenshots and stable video states before accepting the page. Recording support adds motion requirements to this same visual baseline. Preserve artwork aspect ratios and inspect isolated icon artwork; keep control labels and counts editable.

For recordings, connect the visually checked states using the interaction specification, then calibrate motion through [dynamic verification](references/motion-verification.md). Distinguish timed, gesture-following, scroll-driven and asynchronous changes. Missing touchpoints, gestures and precise easing remain inferred or unknown; low-impact conventions must be labeled and critical gaps clarified.

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

For both routes, inspect the actual delivery viewport as well as normalized comparison captures. For a standalone device-reference preview, preserve the reference content proportions; in an existing responsive project preserve its framework and layout behavior, and verify the reference viewport and adaptations separately.

Write `design-qa.md` with source paths, viewport/density, source and render evidence, actual checks, fixes, and remaining differences. Only claim verification for inspected states. If capture is unavailable, deliver the source as unverified and explain the gap.

Report visual fidelity, interaction behavior and motion fidelity separately. Video motion checks supplement every stable state's screenshot checks. Successful clicks, helper validation or a comparison file do not establish visual acceptance. Keep fixable material visual differences in the correction loop; declaring them approximate is not completion. If evidence or tooling genuinely blocks a match, name that specific limit and leave acceptance incomplete.

For skill maintenance, see [validation](references/validation.md). Store user media, generated pages and task QA outside this skill. Audio is outside scope unless requested and inspected.

Return working local preview and source. Identify this as the agent adaptation, not a benchmark of the upstream app or its provider models. Retain the upstream MIT notice with redistributed source.
