# Historical video comparison page

Live URL: <https://zhengads.github.io/MoodCut-dsa4213/>. This directory contains a dependency-free static page, with three native video players, two historical experiment tabs and line changes relative to each experiment's initial plan. It does not invoke models, generate media, collect ratings or change experiment records.

## Sources and presentation boundary

`data.json` is presentation metadata derived from the preserved `docs/pilots/anna-elsa-agent.results.json` and `anna-elsa-actor.results.json` at commit `a466b1bc000889e30af0254126f7c0ec41def436`. It records planned dialogue rather than verified speech transcripts. Five exact provider videos cover six condition entries; actor-v1 generic shares the same video as baseline. V2 confirmation has only offline acceptance and no new video in this page. Original unresolved opinions, fees and rights limitations remain visible; this is not a blind evaluation or a method-quality claim.

The existing `pilot-anna-elsa-20261024` repository Release owns the immutable input files and source attribution. `media.sha256` pins all five MP4s. The source images, credentials, private logs and binary videos are excluded from this directory and from the code branch's Git history.

## Deployment without merging PR #48

`.github/workflows/video-pages.yml` runs when this directory or that workflow changes on `feat/issue-8-agent-animation-pilot` or `main`. Manual dispatch is also declared for later use. Only these two branches are allowed to deploy to the repository's `github-pages` environment. Pages uses workflow deployment, not a source branch build; PR #48 remains unmerged.

The job copies only the five named page files, downloads the five historical MP4 release attachments into the temporary artifact's `media/` directory, verifies their pinned SHA-256 and file count, and uploads/deploys that static artifact with pinned official GitHub Pages actions. No generation client, experiment entry point, paid API or additional account is used. Videos are hosted alongside the page so native players request media from the same origin rather than navigating to Release downloads. The generated artifact contains only regular static files and is not committed back to Git.

## Verification

Verify all six displayed dialogue pairs and file hashes against the preserved result JSON and Release before publishing. Browser checks cover desktop/mobile layout, all five media sources playing, experiment switching, keyboard navigation, no autoplay and pausing other clips when one plays. After deployment, recheck the live page and all five hosted MP4 bytes. Keep the original pilot records and media unchanged; add future experiments explicitly rather than relabeling these historical clips.
