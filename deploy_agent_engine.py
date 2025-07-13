#!/usr/bin/env python3
"""
Deploy PodFlower to Vertex AI Agent Engine
"""

import vertexai
from vertexai.preview import reasoning_engines
import sys
import os
from pathlib import Path
import json

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configuration
PROJECT_ID = "adk-hackathon-dev"  # Your Google Cloud Project ID
LOCATION = "us-central1"  # Supported regions: us-central1, us-east1, europe-west1
STAGING_BUCKET = "gs://podflower-staging-adk-dev"  # Your GCS bucket

class PodFlowerReasoningEngine:
    """
    PodFlower Reasoning Engine wrapper for Agent Engine deployment.
    """
    
    def __init__(self):
        """Initialize the reasoning engine."""
        from pipelines.full_workflow import PodFlowerPipeline
        self.pipeline = PodFlowerPipeline()
    
    def query(self, input_data: dict) -> dict:
        """
        Main query method required by Reasoning Engine.
        """
        try:
            # Get the episode directory from input
            episode_dir = input_data.get("episode_directory", "sample_episode/")
            
            # Run the main pipeline using the execute method
            result = self.pipeline.main_pipeline.execute(
                state={"episode_directory": episode_dir}
            )
            
            return {
                "status": "success",
                "message": "PodFlower pipeline completed successfully",
                "result": result,
                "episode_directory": episode_dir
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"PodFlower pipeline failed: {str(e)}",
                "error_type": type(e).__name__
            }

def deploy_podflower():
    """Deploy PodFlower pipeline to Agent Engine."""
    
    print("🚀 Deploying PodFlower to Vertex AI Agent Engine...")
    
    # Initialize Vertex AI
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )
    
    print("📦 Testing function locally first...")
    
    # Test locally first
    try:
        reasoning_engine = PodFlowerReasoningEngine()
        test_result = reasoning_engine.query({
            "episode_directory": "sample_episode/"
        })
        print(f"✅ Local test result: {test_result['status']}")
        if test_result['status'] == 'error':
            print(f"⚠️ Local test error: {test_result['message']}")
    except Exception as e:
        print(f"❌ Local test failed: {e}")
        return False
    
    print("☁️ Deploying to Agent Engine...")
    
    # Deploy to Agent Engine using ReasoningEngine
    try:
        reasoning_engine = PodFlowerReasoningEngine()
        remote_app = reasoning_engines.ReasoningEngine.create(
            reasoning_engine=reasoning_engine,
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
            display_name="PodFlower-ADK-Production",
            description="End-to-end Japanese podcast automation system using ADK multi-agent workflow"
        )
        
        print(f"🎉 Deployment successful!")
        print(f"📍 Resource Name: {remote_app.resource_name}")
        print(f"🆔 Resource ID: {remote_app.name}")
        
        # Test remote deployment
        print("🧪 Testing remote deployment...")
        try:
            response = remote_app.query(
                input={"episode_directory": "sample_episode/"}
            )
            print(f"✅ Remote test successful!")
            print(f"📊 Response status: {response.get('status', 'unknown')}")
        except Exception as test_error:
            print(f"⚠️ Remote test failed (but deployment succeeded): {test_error}")
        
        return remote_app
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("PodFlower Agent Engine Deployment")
    print("=" * 40)
    
    remote_app = deploy_podflower()
    
    if remote_app:
        print("\n🎉 PodFlower is now live on Agent Engine!")
        print("📋 Next steps:")
        print("1. Use this resource name for your deployment:")
        print(f"   {remote_app.resource_name}")
        print("2. Test your deployment with the Agent Engine API")
        print("3. Record your demo video showing the live system")
        print("\n📝 Save this info for your deployment:")
        print(f"   Project ID: {PROJECT_ID}")
        print(f"   Location: {LOCATION}")
        print(f"   Resource Name: {remote_app.resource_name}")
    else:
        print("\n❌ Deployment failed. Check the errors above.")
        sys.exit(1) 
        