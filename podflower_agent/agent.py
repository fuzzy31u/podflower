"""
PodFlower Agent - Main ADK Web Interface Agent
Wraps the complete PodFlower pipeline as a single agent for adk web.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any
import structlog
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.agents import Agent
from pipelines.full_workflow import PodFlowerPipeline

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env', override=True)

logger = structlog.get_logger()

def process_podcast_episode(episode_directory: str = "sample_episode/") -> dict:
    """
    Process a podcast episode using the PodFlower pipeline.
    
    Args:
        episode_directory (str): Directory containing audio files to process
        
    Returns:
        dict: Processing results including episode package location and status
    """
    try:
        # Initialize the pipeline
        pipeline = PodFlowerPipeline(sample_directory=episode_directory)
        
        # Validate prerequisites
        if not pipeline.validate_prerequisites():
            return {
                "status": "error",
                "error": "Prerequisites validation failed. Check API keys and audio files.",
                "details": "Make sure GOOGLE_API_KEY is set and audio files exist in the episode directory."
            }
        
        # Run the pipeline synchronously for the web interface
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(pipeline.run())
            return {
                "status": "success",
                "message": "PodFlower pipeline completed successfully!",
                "episode_package": result.get("episode_package_dir"),
                "title_candidates": result.get("title_candidates", []),
                "audio_duration": result.get("duration_seconds", 0),
                "details": {
                    "wordpress_url": result.get("wordpress_post_url"),
                    "vercel_url": result.get("vercel_deployment_url"),
                    "x_post_url": result.get("x_tweet_url")
                }
            }
        finally:
            loop.close()
            
    except Exception as e:
        logger.error("Pipeline execution failed", error=str(e))
        return {
            "status": "error", 
            "error": f"Pipeline failed: {str(e)}",
            "details": "Check the logs for more details. Common issues: missing API keys, large audio files (>10MB), or missing audio files."
        }

def get_pipeline_status() -> dict:
    """
    Get the current status of the PodFlower pipeline and environment.
    
    Returns:
        dict: Status information about the pipeline setup
    """
    try:
        # Check environment variables
        api_key = os.getenv('GOOGLE_API_KEY')
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # Check for audio files
        sample_dir = Path("sample_episode")
        audio_files = []
        if sample_dir.exists():
            audio_files = list(sample_dir.glob("*.mp3")) + list(sample_dir.glob("*.mp4")) + list(sample_dir.glob("*.wav"))
        
        # Check assets
        assets_dir = Path("assets")
        has_intro = (assets_dir / "intro.mp3").exists()
        has_outro = (assets_dir / "outro.mp3").exists()
        
        return {
            "status": "success",
            "environment": {
                "google_api_key": "✅ Set" if api_key and len(api_key) > 10 else "❌ Missing or Invalid",
                "google_cloud_project": "✅ Set" if project_id else "❌ Missing",
                "audio_files": len(audio_files),
                "audio_file_names": [f.name for f in audio_files],
                "intro_audio": "✅ Available" if has_intro else "❌ Missing",
                "outro_audio": "✅ Available" if has_outro else "❌ Missing"
            },
            "message": f"Found {len(audio_files)} audio file(s) ready for processing"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Status check failed: {str(e)}"
        }

# Create the main agent for ADK web interface
root_agent = Agent(
    name="podflower_pipeline",
    model="gemini-1.5-flash",
    description="Japanese podcast automation pipeline - transforms raw audio into publication-ready episodes with AI-generated content",
    instruction="""You are PodFlower, an AI-powered Japanese podcast production assistant. 

You can help users:
1. Process podcast episodes from raw audio to publication-ready packages
2. Check the current pipeline status and environment setup
3. Provide guidance on setup and troubleshooting

Key capabilities:
- Audio processing: filler removal, intro/outro addition, professional mastering
- AI content generation: Japanese titles, show notes, ad break detection  
- Multi-platform distribution: Vercel, WordPress, X/Twitter
- Complete automation: 95% time reduction (4 hours → 12 minutes)

When users ask to process an episode, use the process_podcast_episode function.
When users want to check status or setup, use get_pipeline_status function.

Always provide helpful, detailed responses in a friendly tone. If there are errors, explain what went wrong and how to fix it.""",
    tools=[process_podcast_episode, get_pipeline_status]
) 