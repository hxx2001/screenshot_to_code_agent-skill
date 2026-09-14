# Upstream and adaptation

- Repository: https://github.com/abi/screenshot-to-code
- Pinned commit: `d026163f586dfa8c5c10d28c36edd59a9d3b0e88`
- MIT license, copyright (c) 2023 Abi Raja. Full notice: `vendor/LICENSE`.

| Upstream file | Local copy | Runtime use |
| --- | --- | --- |
| `backend/prompts/system_prompt.py` | `vendor/prompts/system_prompt.py` | AST-read general and selected-stack instructions |
| `backend/prompts/create/image.py` | `vendor/prompts/create/image.py` | Render actual screenshot prompt template without importing provider types |
| `backend/codegen/utils.py` | `vendor/codegen/utils.py` | Unchanged `extract_html_content` used by finalize |

The adapter reads the vendored AST without executing its imports or using eval. It keeps the upstream requirements to preserve copy, extract assets, and connect screenshot states, with host-tool mapping.

| Original application | Skill adaptation |
| --- | --- |
| FastAPI/WebSocket orchestrates provider calls | Current conversation agent reads images and writes files |
| Provider-based asset extraction | Measured local crops and available host image tools |
| create_file / edit_file | Host file tools |
| API-managed screenshot_preview | Host browser render, capture and inspection |
| CDN-oriented output | Local assets and dependencies by default |

The unchanged web app still requires API keys. This skill is a replacement orchestration layer, not an unofficial endpoint into a logged-in account. It is not an official upstream skill. Heavy backend/frontend dependencies are unnecessary for this execution mode.

User screenshots and the example H5 stay outside this reusable skill. No private names, user paths or credentials are embedded.

The recording extension uses a local extraction and evidence workflow informed by the user's project video-analysis skill: decoded-frame PTS, coarse-to-dense review and explicit observation boundaries. It does not incorporate project business routes, deployments or diagnostic contracts. New local scripts export native PNG frames, validate interaction evidence and pair motion samples; the current agent remains responsible for interpretation, implementation and real browser verification.
