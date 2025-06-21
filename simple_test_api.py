#!/usr/bin/env python3
"""
Minimal public API for testing PodFlower Agent Engine
Provides judges with public access to test the system
"""

from flask import Flask, jsonify, request, render_template_string
import vertexai
from vertexai.preview import reasoning_engines
import os

app = Flask(__name__)

# Configuration
PROJECT_ID = "adk-hackathon-dev"
LOCATION = "us-central1"
REASONING_ENGINE_ID = "5673805454765981696"

def get_engine():
    """Get the deployed reasoning engine."""
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        resource_name = f"projects/370106061279/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}"
        return reasoning_engines.ReasoningEngine(resource_name)
    except Exception as e:
        print(f"Engine connection failed: {e}")
        return None

@app.route('/')
def index():
    """Simple test interface."""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>PodFlower - ADK Hackathon Demo</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .test-section { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .button { background: #4285f4; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        .button:hover { background: #3367d6; }
        .button:disabled { background: #ccc; cursor: not-allowed; }
        .results { background: #fff; border: 1px solid #ddd; padding: 15px; margin-top: 15px; border-radius: 4px; white-space: pre-wrap; font-family: monospace; max-height: 400px; overflow-y: auto; }
        .success { color: #0f5132; background: #d1e7dd; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .error { color: #842029; background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .spec { background: #e7f3ff; padding: 15px; border-left: 4px solid #0066cc; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌸 PodFlower</h1>
        <h2>Google ADK Hackathon 2025 - Live Demo</h2>
        <p><strong>End-to-End Japanese Podcast Automation System</strong></p>
    </div>

    <div class="spec">
        <h3>📊 System Specifications</h3>
        <ul>
            <li><strong>10 Specialized Agents</strong> - All 3 ADK families (Workflow, LLM, Custom)</li>
            <li><strong>Japanese Language Processing</strong> - Native filler word removal</li>
            <li><strong>Professional Audio Quality</strong> - -16 LUFS, -1 dB peak mastering</li>
            <li><strong>95% Time Reduction</strong> - From 4 hours to 12 minutes</li>
            <li><strong>Multi-platform Distribution</strong> - Vercel, WordPress, X/Twitter</li>
        </ul>
    </div>

    <div class="test-section">
        <h3>🚀 Test the Complete Pipeline</h3>
        <p>Click the button below to execute all 10 agents and see the complete podcast automation in action:</p>
        <button class="button" onclick="testPipeline()" id="testBtn">
            🎬 Run Complete PodFlower Pipeline
        </button>
        <div id="results" class="results" style="display: none;"></div>
    </div>

    <div class="test-section">
        <h3>🎯 What This Demonstrates</h3>
        <ul>
            <li><strong>Technical Implementation (50%)</strong>: 10 agents, all ADK families, production deployment</li>
            <li><strong>Innovation & Creativity (30%)</strong>: Japanese specialization, 95% automation</li>
            <li><strong>Demo & Documentation (20%)</strong>: Live system, comprehensive architecture</li>
        </ul>
    </div>

    <script>
        async function testPipeline() {
            const btn = document.getElementById('testBtn');
            const results = document.getElementById('results');
            
            btn.disabled = true;
            btn.innerHTML = '⏳ Running Pipeline...';
            results.style.display = 'block';
            results.innerHTML = '🚀 Initializing PodFlower Agent Engine...\\n\\n';
            
            try {
                const response = await fetch('/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ episode_directory: 'sample_episode/' })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    results.innerHTML = `✅ SUCCESS: Pipeline completed successfully!

📊 RESULTS SUMMARY:
• Agents Executed: ${data.agents_executed.length}/10
• Processing Time: ${data.technical_details.processing_time}
• Audio Quality: ${data.technical_details.audio_quality}
• Language: ${data.technical_details.language}
• Automation Level: ${data.technical_details.automation_level}

📋 DETAILED OUTPUT:
• Audio Files Found: ${data.results.audio_files.join(', ')}
• Japanese Transcript: "${data.results.transcript}"
• Filler Words Removed: ${data.results.filler_words_removed.join(', ')}
• Title Candidates: ${data.results.title_candidates.length} generated
• Show Notes: ✅ Created with timestamps
• Professional Mastering: ${data.results.lufs} LUFS, ${data.results.peak} dB peak
• Episode Package: ${data.episode_package}

🌐 DISTRIBUTION:
• Vercel URL: ${data.results.vercel_deployment_url}
• WordPress URL: ${data.results.wordpress_post_url}
• X/Twitter URL: ${data.results.x_tweet_url}

🎉 Complete podcast episode ready for publication!`;
                } else {
                    results.innerHTML = `❌ ERROR: ${data.message}\\nError Type: ${data.error_type}`;
                }
                
            } catch (error) {
                results.innerHTML = `❌ Network Error: ${error.message}`;
            }
            
            btn.disabled = false;
            btn.innerHTML = '🎬 Run Complete PodFlower Pipeline';
        }
    </script>
</body>
</html>
    ''')

@app.route('/test', methods=['POST'])
def test():
    """Test endpoint for the pipeline."""
    try:
        data = request.get_json()
        episode_dir = data.get('episode_directory', 'sample_episode/')
        
        engine = get_engine()
        if not engine:
            return jsonify({
                'status': 'error',
                'message': 'Failed to connect to PodFlower Agent Engine',
                'error_type': 'ConnectionError'
            })
        
        response = engine.query(input_data={'episode_directory': episode_dir})
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Test failed: {str(e)}',
            'error_type': type(e).__name__
        })

@app.route('/health')
def health():
    """Health check."""
    return jsonify({
        'status': 'healthy',
        'project_id': PROJECT_ID,
        'reasoning_engine_id': REASONING_ENGINE_ID
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False) 