#!/usr/bin/env python3
"""
PodFlower: Full Workflow Pipeline

This is the main entry point for the momit.fm podcast automation system.
Orchestrates all agents in the correct sequence for end-to-end processing.

Usage:
    python pipelines/full_workflow.py sample_episode/
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict
import structlog
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import all our agents
from agents.recorder.recorder import Agent as RecorderAgent
from agents.filler_removal.filler_removal import Agent as FillerRemovalAgent
from agents.concat_audio.concat_audio import Agent as ConcatAudioAgent
from agents.title_notes.title_notes import Agent as TitleNotesAgent
from agents.ad_break.ad_break import Agent as AdBreakAgent
from agents.mastering.mastering import Agent as MasteringAgent
from agents.export_package.export_package import Agent as ExportPackageAgent
from agents.deploy_vercel.deploy_vercel import Agent as DeployVercelAgent
from agents.wordpress_publish.wordpress_publish import Agent as WordPressPublishAgent
from agents.post_to_x.post_to_x import Agent as PostToXAgent

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class PodFlowerPipeline:
    """PodFlower main pipeline orchestrator."""
    
    def __init__(self, sample_directory: str = "sample_episode/"):
        self.sample_directory = sample_directory
        self.session_service = InMemorySessionService()
        
        # Initialize all agents
        self.recorder_agent = RecorderAgent(watch_directory=sample_directory)
        self.filler_removal_agent = FillerRemovalAgent()
        self.concat_audio_agent = ConcatAudioAgent()
        self.title_notes_agent = TitleNotesAgent()
        self.ad_break_agent = AdBreakAgent()
        self.mastering_agent = MasteringAgent()
        self.export_package_agent = ExportPackageAgent()
        self.deploy_vercel_agent = DeployVercelAgent()
        self.wordpress_publish_agent = WordPressPublishAgent()
        self.post_to_x_agent = PostToXAgent()
        
        # Create the main pipeline using ADK SequentialAgent
        self.main_pipeline = self._create_pipeline()
        
    def _create_pipeline(self) -> SequentialAgent:
        """Create the main pipeline using ADK workflow agents."""
        
        # Phase 1: Core Audio Processing (Sequential)
        audio_processing_pipeline = SequentialAgent(
            name="AudioProcessingPipeline",
            sub_agents=[
                self.recorder_agent,
                self.filler_removal_agent,
                self.concat_audio_agent,
                self.mastering_agent
            ]
        )
        
        # Phase 2: Content Generation (Can run in parallel with audio processing)
        content_generation_pipeline = ParallelAgent(
            name="ContentGenerationPipeline", 
            sub_agents=[
                self.title_notes_agent,
                self.ad_break_agent
            ]
        )
        
        # Phase 3: Package Creation
        package_creation_agent = self.export_package_agent
        
        # Phase 4: Distribution (Parallel deployment)
        distribution_pipeline = ParallelAgent(
            name="DistributionPipeline",
            sub_agents=[
                self.deploy_vercel_agent,
                self.wordpress_publish_agent,
                self.post_to_x_agent
            ]
        )
        
        # Main pipeline orchestration
        main_pipeline = SequentialAgent(
            name="PodFlowerMainPipeline",
            sub_agents=[
                audio_processing_pipeline,
                content_generation_pipeline,  # This will wait for audio processing
                package_creation_agent,
                distribution_pipeline
            ]
        )
        
        return main_pipeline
    
    async def run(self) -> Dict:
        """Execute the full workflow pipeline."""
        logger.info("Starting PodFlower pipeline", 
                   sample_dir=self.sample_directory)
        
        try:
            # Create session
            session = self.session_service.create_session(
                app_name="podflower",
                user_id="system",
                session_id="full_workflow"
            )
            
            # Create runner
            runner = Runner(
                agent=self.main_pipeline,
                app_name="podflower",
                session_service=self.session_service
            )
            
            # Execute pipeline
            logger.info("Executing pipeline...")
            
            # Initialize empty state
            initial_state = {}
            
            # Run the pipeline
            result = await self.main_pipeline.run(initial_state)
            
            logger.info("Pipeline completed successfully", 
                       episode_package=result.get("episode_package_dir"),
                       wordpress_url=result.get("wordpress_post_url"),
                       tweet_url=result.get("x_tweet_url"))
            
            return result
            
        except Exception as e:
            logger.error("Pipeline failed", error=str(e), exc_info=True)
            raise
    
    def validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are met."""
        logger.info("Validating prerequisites...")
        
        # Check sample directory exists
        if not Path(self.sample_directory).exists():
            logger.error("Sample directory does not exist", path=self.sample_directory)
            return False
            
        # Check for audio files in sample directory
        audio_files = list(Path(self.sample_directory).glob("*.mp4")) + \
                     list(Path(self.sample_directory).glob("*.wav")) + \
                     list(Path(self.sample_directory).glob("*.mp3"))
        
        if not audio_files:
            logger.error("No audio files found in sample directory")
            return False
            
        # Check for assets directory
        if not Path("assets").exists():
            logger.warning("Assets directory not found, will need intro.mp3 and outro.mp3")
            
        # Check environment variables
        required_env_vars = [
            "GOOGLE_API_KEY",
            "GOOGLE_CLOUD_PROJECT"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
                
        if missing_vars:
            logger.error("Missing required environment variables", 
                        missing=missing_vars)
            return False
            
        logger.info("Prerequisites validation passed")
        return True


async def main():
    """Main entry point."""
    # Parse command line arguments
    sample_dir = sys.argv[1] if len(sys.argv) > 1 else "sample_episode/"
    
    logger.info("PodFlower Starting", 
               version="0.1.0",
               sample_directory=sample_dir)
    
    # Create pipeline
    pipeline = PodFlowerPipeline(sample_directory=sample_dir)
    
    # Validate prerequisites
    if not pipeline.validate_prerequisites():
        logger.error("Prerequisites validation failed")
        sys.exit(1)
    
    try:
        # Run the pipeline
        result = await pipeline.run()
        
        # Print summary
        print("\n" + "="*60)
        print("🎉 PodFlower Pipeline Completed Successfully!")
        print("="*60)
        print(f"📁 Episode Package: {result.get('episode_package_dir', 'N/A')}")
        print(f"🌐 WordPress Post: {result.get('wordpress_post_url', 'N/A')}")
        print(f"🐦 X Post: {result.get('x_tweet_url', 'N/A')}")
        print(f"🚀 Vercel Deploy: {result.get('vercel_deployment_url', 'N/A')}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error("Pipeline execution failed", error=str(e))
        print(f"\n❌ Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 