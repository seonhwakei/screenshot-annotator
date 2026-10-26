---
name: live-page-verification
description: Use when checking site images, console 404s, live pages, or comparing a rebuilt site route-by-route with a baseline screenshot or its SEO canonical/sitemap host.
category: verification
---

# Live page verification

Judge a page only after its lazy content has loaded: scroll to the bottom, wait, then re-check image load state. A bare `complete === false` on below-the-fold images is a false positive.

## Checks
- Scroll the full page in steps before reading image state, then return to top.
- Fetch each failing image `src` directly. Use the object URL, not the bucket root (a root 403 is normal).
- For console 404s, find the link's real `href` and `curl` it. Framework prefetch of a linked route can 404 on a URL the user never visits; that is not a broken link.
- Read HTTP codes for every route you claim works, and take a screenshot for every claim about layout.

## Reporting
- Separate what was observed (status codes, screenshot, computed style) from what was not checked (other locales, menus not opened, click behavior).
- Report "no bug found" explicitly when nothing is broken, and make no code or deploy change in that case.
