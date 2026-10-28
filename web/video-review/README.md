# Video gallery

The public gallery presents scenarios 01–12 from the current video release, with Baseline, Generic Review and MoodCut playback for each. Its English story briefs are requirements, not dialogue transcripts.

The Pages workflow downloads the release archive and runs `scripts/build_video_gallery.py`. The builder verifies the archive digest and all 36 video hashes against the release index before writing the static site. It never generates media or calls a model. Shared video bytes are explicitly labeled.

To preview locally, run `python scripts/build_video_gallery.py --archive <downloaded-zip> --output <new-site-directory>`, then serve that directory with `python -m http.server --directory <site-directory>`. The output directory must be new so old media cannot leak into deployment.
