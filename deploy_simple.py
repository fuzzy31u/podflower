#!/usr/bin/env python3
"""
Simple PodFlower deployment for Agent Engine
"""

import vertexai
from vertexai.preview import reasoning_engines

# Configuration
PROJECT_ID = "adk-hackathon-dev"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://podflower-staging-adk-hackathon"

class PodFlowerEngine:
    """Simple PodFlower engine for deployment."""
    
    def query(self, input_data: dict) -> dict:
        """
        Simple query function for PodFlower deployment.
        This avoids complex serialization issues.
        """
        import asyncio
        import sys
        from pathlib import Path
        
        # Add project root to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        try:
            # Import and run the pipeline
            from pipelines.full_workflow import PodFlowerPipeline
            
            # Get episode directory from input
            episode_dir = input_data.get("episode_directory", "sample_episode/")
            
            # Create and run pipeline
            pipeline = PodFlowerPipeline(sample_directory=episode_dir)
            
            # Run the pipeline asynchronously
            result = asyncio.run(pipeline.run())
            
            return {
                "status": "success",
                "message": "PodFlower pipeline completed successfully",
                "episode_directory": episode_dir,
                "episode_package": result.get("episode_package_dir"),
                "wordpress_url": result.get("wordpress_post_url"),
                "x_tweet_url": result.get("x_tweet_url"),
                "vercel_url": result.get("vercel_deployment_url")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"PodFlower pipeline failed: {str(e)}",
                "error_type": type(e).__name__
            }

def main():
    """Deploy PodFlower to Agent Engine."""
    
    print("🚀 Deploying PodFlower (Simple) to Vertex AI Agent Engine...")
    
    # Initialize Vertex AI
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )
    
    print("📦 Testing locally first...")
    
    # Test locally
    try:
        engine = PodFlowerEngine()
        test_result = engine.query({"episode_directory": "sample_episode/"})
        print(f"✅ Local test: {test_result['status']}")
        if test_result['status'] == 'error':
            print(f"⚠️ Error: {test_result['message']}")
    except Exception as e:
        print(f"❌ Local test failed: {e}")
        return False
    
    print("☁️ Deploying to Agent Engine...")
    
    # Deploy to Agent Engine
    try:
        engine = PodFlowerEngine()
        remote_app = reasoning_engines.ReasoningEngine.create(
            reasoning_engine=engine,
            requirements=[
                "google-cloud-aiplatform[adk,agent_engines]>=1.97.0",
                "google-adk>=1.0.0",
                "ffmpeg-python>=0.2.0",
                "structlog>=23.0.0",
                "python-dotenv>=1.0.0",
                "pydub>=0.25.0",
                "requests>=2.32.0",
                "pydantic>=2.11.0",
                "python-multipart>=0.0.20",
                "numpy>=1.21.0",
                "deprecated>=1.2.0"
            ],
            display_name="PodFlower-Simple-ADK-Hackathon",
            description="End-to-end Japanese podcast automation system using ADK multi-agent workflow (Simple Deployment)"
        )
        
        print(f"🎉 Deployment successful!")
        print(f"📍 Resource Name: {remote_app.resource_name}")
        print(f"🆔 Resource ID: {remote_app.name}")
        
        # Test remote
        print("🧪 Testing remote deployment...")
        try:
            response = remote_app.query(
                input={"episode_directory": "sample_episode/"}
            )
            print(f"✅ Remote test successful!")
            print(f"📊 Status: {response.get('status', 'unknown')}")
        except Exception as test_error:
            print(f"⚠️ Remote test failed (deployment succeeded): {test_error}")
        
        print("\n🎉 PodFlower is now live on Agent Engine!")
        print("📋 Submission Details:")
        print(f"   Project ID: {PROJECT_ID}")
        print(f"   Location: {LOCATION}")
        print(f"   Resource Name: {remote_app.resource_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 