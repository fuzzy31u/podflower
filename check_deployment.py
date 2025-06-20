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
                    # Use the correct predict method for reasoning engines
                    response = engine.predict(
                        input_data={"episode_directory": "sample_episode/"}
                    )
                    print(f"✅ Test successful: {response.get('status', 'unknown')}")
                    if response.get('status') == 'success':
                        print(f"📁 Episode package: {response.get('episode_package', 'N/A')}")
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