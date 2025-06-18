# Assets Directory

This directory contains audio assets used by the PodFlower pipeline.

## Required Files

- `intro.mp3` - Podcast intro music/announcement (required)
- `outro.mp3` - Podcast outro music/credits (required)

## Audio Specifications

### Recommended Format
- Format: MP3
- Sample Rate: 44.1 kHz
- Bit Rate: 192 kbps or higher
- Channels: Stereo (2 channels)

### Duration Guidelines
- **Intro**: 10-30 seconds
- **Outro**: 15-45 seconds

## File Requirements

Both files must be present for the concat_audio agent to function properly. The pipeline will fail if either file is missing.

## Example Structure

```bash
assets/
├── intro.mp3           # Podcast intro
├── outro.mp3           # Podcast outro
└── README.md          # This file
```

## Creating Your Assets

1. Record or source your intro/outro audio
2. Edit to appropriate length
3. Export as MP3 with the specifications above
4. Place in this directory with exact filenames: `intro.mp3` and `outro.mp3`

## Testing

You can test your assets by running:

```bash
ffmpeg -i assets/intro.mp3 -i assets/outro.mp3 -f null -
```

This will validate that both files are readable by ffmpeg. 