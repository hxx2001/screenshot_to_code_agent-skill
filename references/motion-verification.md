# Dynamic verification

## Capture real behavior

Match content region, CSS viewport, device scale and initial state. Use available host browser automation/recording, reading its current API first. This skill supplies no browser driver and assumes no particular Playwright/CDP API. Keep source and rendered recordings separate.

Exercise real controls in source order. Capture opening, travel, settling and demonstrated close/return paths. Repeat a cycle; check interruption/rapid inputs when relevant. Record steps and browser errors. Forcing an end state does not verify that clicks/gestures work.

Real capture verifies event paths and natural timing. Controlled captures that pause/seek animation may supplement geometry checks; label them controlled. A screenshot request timestamp is not necessarily its captured frame time. Without recording/capture tools, perform available interaction checks and mark dynamic matching unverified.

## Align without hiding differences

Extract dense frames from both recordings with `video_frames.py`. Document any crop/scale and preserve originals. The comparison helper requires equal exported dimensions and never silently rescales.

Pick onset independently from inspected frames. Align by onset, preserving elapsed time. Compare intermediate motion, settling and a post-settle hold. Do not stretch timelines to force endpoints to coincide. Onset alignment excludes input-to-motion latency; measure it separately when visible input evidence exists.

```bash
python3 <skill>/scripts/motion_compare.py \
  --reference /absolute/source/index.json --render /absolute/render/index.json \
  --reference-start 2.5 --render-start 0.8 \
  --offsets 0,0.05,0.1,0.15,0.2,0.3,0.4 --tolerance 0.025 \
  --out /absolute/work/motion-comparison
```

Times above are examples, in seconds relative to each full recording's first decoded frame. Nearest actual frames are paired; requested/actual times and errors are recorded. Out-of-range or out-of-tolerance samples fail. Choose tolerance from source spacing, not to conceal missing frames. Inspect errors before judging images. Reused frames are reported and limit precision.

For gesture/scroll behavior align comparable input displacement too. Use observed anchors and explicit pairs with still-image compare; timing alone cannot prove tracking, thresholds, velocity or inertia. Record missing input evidence.

## Focus on a region

Add one or more regions to the same command, for example:

```text
--region drawer:0,300,390,844 --region button:250,650,380,730
```

Boxes are `[left, top, right, bottom]` in the already normalized, equal-sized exported images; right/bottom are exclusive. They are fixed coordinates, not CSS units or automatic tracking. Include the complete path of a moving element and inspect other regions separately. Out-of-bounds boxes fail rather than clipping or scaling silently.

Full-frame pairs, overlays and difference images are always retained. Each region gets its own native-size pair, overlay and difference image at every compared time. `comparison.json` also records per-region and full-frame mean absolute channel error (0–255) and the fraction of pixels with any channel difference at least 12/255. These diagnostics help locate differences; they are not similarity scores or acceptance thresholds. A clean drawer crop does not establish that the rest of the page is correct.

## Judge and report

Inspect contact sheet, pairs and overlays for geometry, motion order, clipping, backdrop, endpoint, overshoot and settling. Optional position/time plots use measured points and distinguish fits. Pixel equality is not a fidelity score; fonts, compression and irrelevant regions can dominate it.

Fix meaningful discrepancies, replay affected interactions and update their verification records. In `design-qa.md` separate stable appearance, real event/state checks, intermediate motion/timing checks, and inferred/unobserved behavior. Cover every requested transition, including pending/blocked ones. Local replay does not prove exact original easing, complete coverage or production/backend equivalence.

For `passed` animation verification, follow the [evidence requirements](interaction-spec.md#passing-an-animation-check). Reports now use version 2. Generate a report spanning the specified motion window endpoints and intermediate frames from densely extracted recordings, then record actual visual and interaction reviews. Pairing may produce reports with reused frames or cross-recording time skew for inspection; such reports cannot pass the stricter verification gate. Keep tolerance justified by frame spacing.
