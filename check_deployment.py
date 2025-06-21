#!/usr/bin/env python3
"""
Check PodFlower deployment status
"""

import vertexai
from vertexai.preview import reasoning_engines

# Configuration
PROJECT_ID = "adk-hackathon-dev"
LOCATION = "us-central1"

def check_deployments():
    """Check existing reasoning engine deployments."""
    
    print("🔍 Checking PodFlower deployments...")
    
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    try:
        # List all reasoning engines
        engines = reasoning_engines.ReasoningEngine.list()
        
        print(f"📊 Found {len(engines)} reasoning engines:")
        
        for engine in engines:
            print(f"  📍 {engine.display_name or 'Unnamed'}")
            print(f"     Resource: {engine.resource_name}")
            print(f"     Created: {engine.create_time}")
            print()
            
            # If it's our PodFlower deployment, test it
            if "PodFlower" in (engine.display_name or ""):
                print(f"🧪 Testing {engine.display_name}...")
                try:
                    # Create a remote client for the deployed engine
                    remote_engine = reasoning_engines.ReasoningEngine(engine.resource_name)
                    
                    # Query the deployed engine
                    response = remote_engine.query(
                        input_data={"episode_directory": "sample_episode/"}
                    )
                    status = response.get('status', 'unknown')
                    print(f"📊 Test result: {status}")
                    
                    if status == 'success':
                        print(f"✅ Pipeline completed successfully!")
                        print(f"📁 Episode package: {response.get('episode_package', 'N/A')}")
                        print(f"🌐 WordPress URL: {response.get('wordpress_url', 'N/A')}")
                        print(f"🐦 X Tweet URL: {response.get('x_tweet_url', 'N/A')}")
                        print(f"⚡ Vercel URL: {response.get('vercel_url', 'N/A')}")
                    else:
                        print(f"❌ Pipeline failed: {response.get('message', 'Unknown error')}")
                        print(f"🔍 Error type: {response.get('error_type', 'Unknown')}")
                except Exception as e:
                    print(f"❌ Test failed: {e}")
                print()
        
        return engines
        
    except Exception as e:
        print(f"❌ Failed to list deployments: {e}")
        return []

if __name__ == "__main__":
    engines = check_deployments()
    
    if not engines:
        print("No deployments found. The deployment might still be in progress.")
    else:
        print(f"✅ Found {len(engines)} deployments!") 