# Interaction specification, version 1

Write `interaction-spec.json` in the task output directory. Paths resolve relative to it; each source points to a `video_frames.py` index. Screenshots can be extra `prepare --image` inputs. Measurements are estimates, not recovered source code.

Example (replace every sample/frame value with actual evidence):

```json
{
  "version": 1,
  "viewport": {"width": 390, "height": 844, "dpr": 1, "normalization": "Same content area; status bar excluded"},
  "sources": {"clip": "frames/run/index.json"},
  "reviewed_ranges": [{"source": "clip", "start_frame": 0, "end_frame": 18, "density": "every-frame"}],
  "states": [
    {"id": "closed", "description": "Drawer closed", "evidence": [{"source": "clip", "frame_number": 0}]},
    {"id": "open", "description": "Drawer settled", "evidence": [{"source": "clip", "frame_number": 18}]}
  ],
  "transitions": [{
    "id": "open-drawer", "from": "closed", "to": "open",
    "trigger": {"description": "Click Choose", "basis": "inferred", "evidence": []},
    "motion": {
      "kind": "timed",
      "window": {"source": "clip", "start_frame": 1, "end_frame": 18},
      "tracks": [{"element": "drawer", "property": "top", "unit": "source-px", "basis": "observed", "samples": [{"frame_number": 1, "value": 844}, {"frame_number": 9, "value": 530}, {"frame_number": 18, "value": 400}]}],
      "easing": {"value": "ease-out", "basis": "inferred"},
      "uncertainty": "Onset bounded by adjacent frames; exact easing and click location unavailable"
    },
    "implementation": "Button opens drawer. Backdrop dismissal is a conventional assumption.",
    "verification": {"status": "pending", "evidence": [], "notes": ""}
  }],
  "unseen_controls": [{"description": "Checkout", "decision": "Ask for behavior if required; keep visibly unavailable meanwhile", "basis": "unknown"}]
}
```

Validate with `python3 <skill>/scripts/interaction_spec.py /absolute/work/interaction-spec.json`.
Validation checks IDs, frame availability, increasing samples, windows, reviewed coverage, and observed-trigger evidence. It cannot prove visual inspection or interpretation. Additional descriptive fields are allowed.

`basis`: `observed`, `user-described`, `inferred`, `unknown`.
`motion.kind`: `timed`, `gesture`, `scroll`, `state`, `none`.
Each window references one index spanning the transition. Tracks use frames from that window. Geometry can be measured; opacity/easing usually remain inferred.

States require frame evidence, or explicit `basis` of `user-described`/`inferred`/`unknown` and a description. Undemonstrated transitions use `motion.window: null`, empty tracks and a trigger that is not observed. Their verification cannot be passed as video fidelity. Status is `pending`, `partial`, `blocked` or `passed`; passing requires a demonstrated window and actual replay evidence paths/links. A comparison exit code alone is not acceptance.

`reviewed_ranges` records actual review, with `density` of `every-frame` or `sampled`. Every-frame ranges require consecutive extracted frame numbers and actual review of all frames. Sparse overview remains sampled. An unseen control is not a requirement to invent a flow: label low-impact conventions, or ask about a critical missing outcome.
