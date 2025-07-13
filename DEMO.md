# PodFlower Demo Guide

This guide walks through demonstrating the complete PodFlower system.

## Quick Demo (5 minutes)

### Prerequisites
1. **Google API Key** from Google AI Studio
2. **Sample audio file** (any MP4/WAV from Zoom/Riverside)
3. **Python 3.11+** with pip installed

### One-Command Demo
```bash
# 1. Setup (30 seconds)
git clone <repository>
cd podflower
pip install -r requirements.txt
cp env.example .env
# Edit .env with your GOOGLE_API_KEY

# 2. Add sample audio (30 seconds)
# Place any audio file in sample_episode/ directory
cp your_recording.mp4 sample_episode/

# 3. Create assets (optional - will use defaults if missing)
mkdir -p assets
# Add intro.mp3 and outro.mp3 or use provided samples

# 4. Run complete pipeline (2-3 minutes)
python pipelines/full_workflow.py sample_episode/
```

**Expected Output:**
```
🎉 PodFlower Pipeline Completed Successfully!
============================================================
📁 Episode Package: build/20241201_episode01/
🌐 WordPress Post: https://momithub.com/episode-title
🐦 X Post: https://x.com/momitfm/status/123456789
🚀 Vercel Deploy: https://hub-momit-fm.vercel.app
============================================================
```

## Detailed Demo Walkthrough

### 1. Agent Architecture Demo

Show the multi-agent system in action:

```bash
# Enable verbose logging to see agent orchestration
LOG_LEVEL=DEBUG python pipelines/full_workflow.py sample_episode/
```

**Key Points to Highlight:**
- **10 specialized agents** working in coordination
- **ADK workflow patterns** (Sequential, Parallel, Loop)
- **State sharing** between agents via pipeline state
- **Error handling** and graceful degradation

### 2. Japanese Language Processing Demo

Demonstrate language-specific features:

```bash
# Use Japanese audio sample
# Pipeline will show:
# - Japanese Speech-to-Text transcription
# - Filler word detection ("えーと", "あのー", etc.)
# - Japanese title generation
# - Cultural-appropriate ad break placement
```

**Sample Output:**
```json
{
  "title_candidates": [
    "AI時代のプログラマーの未来",
    "スタートアップの現実と理想", 
    "テクノロジーが変える働き方",
    "エンジニアのキャリア戦略",
    "今週のテック話題をディープダイブ"
  ],
  "shownote_md": "# 概要\n今回のエピソードでは..."
}
```

### 3. Multi-Platform Distribution Demo

Show automated distribution to multiple platforms:

```bash
# With full API keys configured, pipeline will:
# 1. Deploy to Vercel (static site)
# 2. Publish to WordPress (with featured image)
# 3. Post to X/Twitter (with Japanese formatting)
# All in parallel!
```

### 4. Quality Metrics Demo

Demonstrate professional audio processing:

```bash
# Before and after audio analysis
ffprobe -f lavfi -i amovie=sample_episode/raw_audio.mp4,astats=metadata=1:reset=1 -show_entries frame=pkt_pts_time:frame_tags=lavfi.astats.Overall.RMS_level -of csv=p=0

# After mastering - shows -16 LUFS / -1 dB normalization
ffprobe -f lavfi -i amovie=build/episode01/episode_final.mp3,astats=metadata=1:reset=1 -show_entries frame=pkt_pts_time:frame_tags=lavfi.astats.Overall.RMS_level -of csv=p=0
```

## Test Suite Demo

### Unit Tests
```bash
# Show comprehensive test coverage
make test-unit

# Specific agent tests
pytest tests/test_agents.py::TestRecorderAgent -v
pytest tests/test_agents.py::TestTitleNotesAgent -v
```

### Integration Tests  
```bash
# End-to-end pipeline test
make test-e2e

# Performance benchmarks
make bench
```

### Code Quality
```bash
# Type checking with mypy --strict
make type-check

# Code formatting
make format

# Linting
make lint
```

## Architecture Demo

### ADK Agent Types in Action

**1. Workflow Agents (Orchestration)**
```python
# Show how SequentialAgent coordinates phases
main_pipeline = SequentialAgent(
    name="PodFlowerMainPipeline",
    sub_agents=[
        audio_processing_pipeline,    # Sequential
        content_generation_pipeline,  # Parallel
        package_creation_agent,      # Single
        distribution_pipeline        # Parallel
    ]
)
```

**2. LLM Agents (Reasoning)**
```python
# Show intelligent content generation
title_notes_agent = LlmAgent(
    model="gemini-2.0-flash",
    instruction="Japanese podcast editor instructions...",
    tools=[]  # Pure reasoning task
)
```

**3. Custom Agents (Specialized Logic)**
```python
# Show audio processing specialization
class FillerRemovalAgent(BaseAgent):
    async def run(self, state: Dict) -> Dict:
        # STT + filler detection + audio cutting
        # Google Cloud Speech-to-Text integration
        # Japanese language processing
```

## Demo Variations

### Minimal Demo (No External APIs)
```bash
# Set environment to skip optional integrations
export SKIP_AGENTS=deploy_vercel,wordpress_publish,post_to_x
python pipelines/full_workflow.py sample_episode/
```

### Development Demo
```bash
# Show development workflow
make setup-dev
make test
make demo  # Runs with verbose logging
```

### Docker Demo
```bash
# Containerized execution
make docker-build
make docker-run
```

## Expected Results

### Episode Package Structure
```
build/20241201_episode01/
├── episode_final.mp3      # Mastered audio (-16 LUFS / -1 dB)
├── shownote.md           # Japanese show notes
└── meta.json             # Complete metadata
    ├── title: "Selected title"
    ├── title_candidates: [5 options]
    ├── duration_seconds: 1847.3
    ├── ad_timestamps: ["15:30", "32:45"]
    ├── sha256_checksum: "abc123..."
    └── created_at: "2024-12-01T10:30:00"
```

### Performance Metrics
- **Pipeline Duration**: 3-5 minutes for 60-minute episode
- **Audio Quality**: Professional broadcast standards
- **STT Accuracy**: ≤5% word error rate (Japanese)
- **Test Coverage**: ≥90% (unit + integration)

## Troubleshooting

### Common Issues

**Missing Google API Key**
```bash
# Error: "Missing required environment variables"
# Solution: Set GOOGLE_API_KEY in .env file
```

**No Audio Files Found**
```bash
# Error: "No new audio files found in watch directory"
# Solution: Add .mp4/.wav files to sample_episode/
```

**FFmpeg Not Found**
```bash
# Error: "FFmpeg not found"
# Solution: Install FFmpeg
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
```

### Debug Mode
```bash
# Enable maximum verbosity
LOG_LEVEL=DEBUG python pipelines/full_workflow.py sample_episode/
```

## Demo Script for Presentation

1. **Introduction (30 seconds)**
   - "PodFlower automates Japanese podcast production with 10 AI agents"
   - "From raw recording to social media in one command"

2. **Architecture Overview (60 seconds)**
   - Show mermaid diagram
   - Explain agent types and orchestration patterns
   - Highlight Japanese language specialization

3. **Live Demo (3 minutes)**
   - Run one-command demo
   - Show real-time agent execution
   - Display final results and quality metrics

4. **Technical Deep Dive (60 seconds)**
   - Code walkthrough of key agents
   - Test suite execution
   - Quality metrics validation

5. **Q&A (30 seconds)**
   - Address questions about implementation
   - Discuss potential extensions and scaling

This demo showcases how ADK enables sophisticated multi-agent orchestration to solve real-world automation challenges in the Japanese podcast industry. 