# Vendored front-end libraries

Pinned copies, served locally so the UI works offline. Fetched from jsDelivr on 2026-10-13
(see `specs/001-chat-beside-files/research.md` R4). Only the trailing `sourceMappingURL`
comments were removed; the code is unchanged.

| File | Package | Version | License |
|---|---|---|---|
| `marked.umd.js` | [marked](https://github.com/markedjs/marked) | 18.0.14 | MIT |
| `purify.min.js` | [DOMPurify](https://github.com/cure53/DOMPurify) | 3.4.16 | Apache-2.0 OR MPL-2.0 |
| `highlight.min.js` (common bundle) | [highlight.js](https://github.com/highlightjs/highlight.js) (`@highlightjs/cdn-assets`) | 11.12.0 | BSD-3-Clause |
| `scala.min.js`, `dockerfile.min.js` | highlight.js languages | 11.12.0 | BSD-3-Clause |
| `github.min.css`, `github-dark.min.css` | highlight.js styles | 11.12.0 | BSD-3-Clause |

To update: change the versions in research.md, re-download the same paths, and strip the
`sourceMappingURL` lines again.
