# Sample Episode Directory

This directory contains sample audio files for testing the ADK-PodFlow pipeline.

## Required Files

Place your raw audio files (from Zoom/Riverside recordings) in this directory:

- `raw_audio.mp4` - Main audio track
- `guest_track.mp4` - Guest audio track (optional)

## Supported Formats

- `.mp4` (Zoom/Riverside default)
- `.wav` (uncompressed audio)
- `.m4a` (Apple audio)
- `.mp3` (compressed audio)

## File Naming

The system will automatically detect and process audio files in this directory. The first file found will be used as the main audio track.

## Example

```bash
sample_episode/
├── raw_audio.mp4        # Main recording
├── guest_track.mp4      # Guest track (optional)
└── README.md           # This file
```

## Usage

```bash
python pipelines/full_workflow.py sample_episode/
``` 