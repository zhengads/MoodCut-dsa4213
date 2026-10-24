# MovieAgent animation reference library

This library indexes **75 images for 25 characters from four animated films**, plus 25 upstream character captions. The 100 original files total 56,989,354 bytes. Images and captions are downloaded into the ignored `assets/raw/movieagent/` directory; Git contains the provenance, selection and integrity metadata, not the original pictures. This is a local reference library, not a new evaluation dataset or a formal experiment sample.

| Upstream film directory | Characters | Images |
| --- | --- | ---: |
| FrozenII | Anna, Elsa, Kristoff, Mattias, Olaf | 15 |
| DespicableMe4 | Gru, Lucy, Maxime, Minions, Prescott, Valentina | 18 |
| InsideOut2 | Anger, Anxiety, Disgust, Envy, Fear, Joy, Riley, Sadness | 24 |
| NeZha2 | Aobing, Ladyyin, Lijing, Nezha, Shenggongbao, Taiyi | 18 |

Each character has the upstream `best.png` and the first two other distinct Git blob IDs in lexicographic source-path order. `primary_asset_id` identifies `best.png`; this label comes from the upstream filename, not our own quality ranking. The two extra images are additional reference candidates, not manually approved crops or guaranteed single-person portraits. Only `full` framing is enabled. Original bytes, backgrounds and source filenames are retained; nothing is cropped, retouched or regenerated. Live-action film directories, audio, video, weights and upstream executable code are excluded.

## Source and rights

- Source repository: [showlab/MovieAgent](https://github.com/showlab/MovieAgent).
- Fixed source revision: [`d84041bed8bc8be460664528d9e9924cdde384ba`](https://github.com/showlab/MovieAgent/tree/d84041bed8bc8be460664528d9e9924cdde384ba/dataset).
- Research attribution: Weijia Wu, Zeyu Zhu and Mike Zheng Shou, *MovieAgent: Automated Movie Generation via Multi-Agent CoT Planning*, 2025, [arXiv:2503.07314](https://arxiv.org/abs/2503.07314). Upstream citation is preserved in our [reference notes](../../docs/REFERENCES.md).
- These pictures depict third-party film characters. MovieAgent is the immediate source; its authors are not thereby established as the owners of the underlying film/character rights. Those rights remain with the respective rights holders.
- At the fixed revision, the repository has no project-level LICENSE or image-specific grant found for these files. A nested backend license does not authorize the film images. GitHub also reports no repository license at the 2026-10-24 check. **Attribution and a public download URL do not establish permission or guarantee non-infringement.**
- Rights remain **unconfirmed**. Do not describe these files as CC, MIT, public domain, commercially cleared or authorized for public redistribution. Local caching is a technical operation, not a finding that any particular use is legally permitted. Before public redistribution, commercial use or publication of derived material, establish the rights needed for that use or choose material with an appropriate explicit license.

The metadata explicitly records `rights_status=unconfirmed`, `public_redistribution_authorized=false` and `commercial_use_cleared=false`. No new image host, release attachment or public image upload is created by this import. Preserve the source and rights notes when selecting assets; do not apply the sigils-people portrait license to this separate library.

## Reproduce and verify

Reuse the existing reference downloader and local AssetManifest builder:

```bash
# Explicitly download only the pinned animation selection plus the core references.
python scripts/prepare_references.py --animation-assets

# Offline, read-only integrity check; a missing or changed file fails.
python scripts/prepare_references.py --animation-assets --check

# Independently verify the committed manifest against the actual local image bytes.
python scripts/prepare_assets.py --selection assets/library/movieagent-animation.selection.json --output assets/library/movieagent-animation.manifest.json --check
```

The default download and legacy `--assets` scope remain unchanged. Combining `--assets --animation-assets` checks/downloads shared files once; conflicting identities fail before any download. Existing files are checked first and never overwritten. `--check` performs no network requests. No model/API generation, voice cloning or upstream entrypoint execution is involved.

Files:

- [Source lock](movieagent-animation.sources.lock.json): fixed URLs, source revision, Git blob SHA-1, size and SHA-256 for all 100 files. Initial import matched bytes against the fixed Git tree's blob identity; subsequent downloads use the locked size/SHA-256.
- [Selection and character index](movieagent-animation.selection.json): 25 character names/film directories, primary asset IDs, source captions, 75 explicit image selections and rights status.
- [AssetManifest](movieagent-animation.manifest.json): the existing 1.0 asset schema, including each image's dimensions, byte hash, source URL, full framing and rights note. It does not replace `assets/manifest.json` or alter existing run identities.

Choose and inspect the needed characters/images before a future run. A single explicitly authorized Anna/Elsa probe on 2026-10-24 used the unchanged primary PNGs with HeyGen 768p, requested five seconds and the fixed line “伞还给你。”. It completed with one POST, a returned $0.25 charge and a real video/audio file. This establishes acceptance of those two inputs for that task, not rights clearance, universal provider acceptance, or proof that the other 73 images work. It was a handwritten material probe, not an actual planning/review Agent output or method evaluation. Its private receipts remain in ignored `runs/anna-elsa-heygen-20261024/`; there are no additional paid calls in this import.
