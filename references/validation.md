# Screenshot baseline and recording extension validation

## Baseline preservation audit, 2026-09-11

Compared the installed upgrade directly with screenshot-only commit `ffd43c5ba4273dcde264586ee0c391d6d0c3d598`, extracted into a separate local directory. The original SKILL workflow body is retained; recording routing, shared visual acceptance and motion verification are additions. The default invocation and README also retain screenshot-first page implementation and correction.

- The four vendored upstream files and upstream manifest are byte-identical to the initial version.
- Original screenshot briefs are byte-identical in 18 cases: all six supported stacks, each with one image, multiple images and repeated images in a specified order.
- Original crop image/provenance manifest, HTML extraction for raw/fenced/file-wrapped input, side-by-side comparison and overlay outputs are byte-identical. Unequal image dimensions still fail with the original error.
- Fixed compatibility for callers that use the original `prepare` argument namespace without `interaction_spec`, and preserved the screenshot sequence. Video frames are appended only when a specification is provided.
- Current regression suite: 11 tests passed, none skipped, including original-call compatibility, screenshot preparation with standard-library-only Python and no executable PATH, mixed screenshot/video input, and real FFmpeg VFR extraction.

This establishes preservation of the checked workflow requirements, source prompts and helper behavior. It does not prove equal generated-page quality across all agent runs. The real recording trial exposed missed visual correction despite successful interactions; [page fidelity](page-fidelity.md) now makes the original visual correction loop explicit for both routes. Each generated page still needs final browser inspection; helper tests cannot grant visual acceptance.

When maintaining the upgrade, compare original screenshot commands and outputs against the baseline as well as running the current suite. Keep audit copies and media in the task output directory rather than the installed skill.

## Earlier recording helper and browser validation

Local validation performed on 2026-09-11. This is evidence about the helper workflow, not a guarantee of reconstruction fidelity.

- Skill Creator frontmatter validation: passed.
- Python regression suite: 8 tests passed, including real FFmpeg extraction; no tests skipped. Covers 1400px native PNG export, nonzero initial PTS and variable frame intervals, invalid timestamps/600-frame bounds, invalid evidence/false pass records, still-image and video briefs, crop/HTML extraction, temporal gaps/dimension mismatches, repeated nearest frames, and matching endpoints with a different intermediate frame.
- Browser smoke: locally generated drawer fixture, Chrome through Playwright, 360×640 CSS pixels at DPR 1. Three real recordings: reference 400ms, repeat 400ms, variant 800ms. Actual button clicks opened, closed and reopened the drawer; no browser page errors. DOM sampling captured intermediate positions.
- Recordings were extracted at native size and paired at 8 elapsed-time offsets. The two 400ms runs had matching intermediate drawer positions at the inspected +240ms pair; the 800ms variant visibly lagged and had a lighter backdrop. Both compared pairs were inspected as images.
- Pixel-based first-visible-motion to settled measurements were about 360ms for both 400ms fixtures, and 800ms for the slower fixture. These are sampled visible intervals, not a claim to recover the exact authored duration; frame cadence and onset selection limit precision.
- Generated video index → interaction specification → validated build brief ran successfully. The fixture specification remains partial verification; automated scans and selected pair inspection are not full manual frame review.

Still unverified: independent reconstruction from an external user recording, full multi-screen navigation, gesture velocity/inertia, spring fitting, audio, and device/App WebView equivalence. These require actual task evidence. No reference recordings or generated pages are bundled in the skill.

To repeat helper regression: `python3 -m unittest discover -s scripts -p 'test_*.py' -v` from the skill directory. FFmpeg/FFprobe and Pillow are needed to run all checks. Browser acceptance is a separate real recording exercise described in [motion-verification.md](motion-verification.md).
