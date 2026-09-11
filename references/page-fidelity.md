# Page fidelity: shared by screenshots and recordings

The output is editable frontend code matching the supplied visual states. A recording adds transitions; it does not make stable-state fidelity optional. Apply this reference while building and reviewing the page, not only when writing the final QA report.

## Establish the visual target

For every supplied screenshot or selected stable video state, record the source, content crop, target CSS viewport/DPR and scroll position. Distinguish independent pages from tabs or states; connect known relationships and keep unrelated screenshots separately accessible. For mixed inputs, preserve each source's version and state. A clearer screenshot refines the corresponding video's state, not unrelated states.

Measure the features that determine the page's appearance:

| Area | Compare against the source |
| --- | --- |
| Layout | Container width, margins, column gaps, element bounds, fixed/scroll regions, first-screen content cutoff |
| Text | Exact copy and numbers, font family or documented substitute, size, weight, line height, wrapping and truncation |
| Assets | Correct crop, native sharpness, aspect ratio, icon shape/stroke, avatars and integral artwork |
| Styling | Colors, background, borders, radii, shadows, selection and disabled states |

Use real semantic controls and editable text. Prefer available supplied assets and isolated icon artwork to visibly different approximations. Inspect extracted assets at their intended size. Where a larger asset is needed, seek a clearer supplied screenshot/native frame first; use available host image tools for missing or low-resolution artwork as the build brief describes. Preserve provenance and distinguish reconstructed assets from originals. Keep follow-up edits scoped to the selected element and the code that renders it.

## Correct and recapture

Capture the real browser rendering at the declared target size/DPR, then compare equivalent regions side by side. Inspect both the entire page and focused crops for the largest differences. Record each material mismatch with its source location, correction and final capture. Fix layout, wrong text/line wrapping, stretched imagery and substituted prominent icons before treating the state as complete. Recheck affected states after shared styles, fonts or motion code change.

A comparison artifact is not evidence of inspection, and pixel equality is not a quality score. A successful build, click path or animation cannot compensate for a visible page mismatch. An unsupported label such as “approximately recreated” does not close a fixable issue. Continue correction until material differences are resolved; if the supplied source or tool access prevents resolution, record the concrete missing evidence and leave that item open.

Also inspect the preview at the size the user will actually see. Reference normalization must not hide changed proportions, clipping or content density there. Check mobile/desktop adaptations when applicable to the requested page, and keep the reference-size result distinct from those adaptations. This does not require redesigning an existing responsive app into a fixed screenshot.

## Acceptance evidence

In the task's `design-qa.md`, map each state to its source and final render, viewport/crop, important differences and disposition. Record three separate outcomes: stable visual fidelity, implemented controls/state changes, and motion fidelity (not applicable for screenshots without motion evidence). List specific open items; do not report the whole recreation as passed while material visual issues remain.

Controls within screenshot scope still need behavior checks when implemented: navigation, tabs/toggles, expanded replies, input validation, persistence and return paths. A screenshot-only request can complete this original workflow without a video, frame index or interaction specification.
