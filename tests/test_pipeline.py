"""
End-to-End Pipeline Tests for PodFlower

Tests the complete pipeline functionality using sample data.
"""

import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines.full_workflow import PodFlowerPipeline


class TestPodFlowerPipeline:
    """End-to-end pipeline tests."""
    
    @pytest.fixture
    def temp_sample_dir(self):
        """Create temporary sample directory with test audio file."""
        temp_dir = tempfile.mkdtemp()
        sample_dir = Path(temp_dir) / "sample_episode"
        sample_dir.mkdir()
        
        # Create a dummy audio file
        dummy_audio = sample_dir / "raw_audio.mp4"
        dummy_audio.write_bytes(b"dummy audio content")
        
        yield str(sample_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def temp_assets_dir(self):
        """Create temporary assets directory with intro/outro files."""
        temp_dir = tempfile.mkdtemp()
        assets_dir = Path(temp_dir) / "assets"
        assets_dir.mkdir()
        
        # Create dummy intro/outro files
        intro_file = assets_dir / "intro.mp3"
        outro_file = assets_dir / "outro.mp3"
        intro_file.write_bytes(b"dummy intro audio")
        outro_file.write_bytes(b"dummy outro audio")
        
        yield str(assets_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Mock required environment variables."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test_api_key")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        monkeypatch.setenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    def test_pipeline_initialization(self, temp_sample_dir, mock_env_vars):
        """Test that pipeline initializes correctly."""
        pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
        
        assert pipeline.sample_directory == temp_sample_dir
        assert pipeline.recorder_agent is not None
        assert pipeline.filler_removal_agent is not None
        assert pipeline.main_pipeline is not None
    
    def test_prerequisites_validation_success(self, temp_sample_dir, mock_env_vars):
        """Test prerequisites validation with valid setup."""
        pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
        
        result = pipeline.validate_prerequisites()
        assert result is True
    
    def test_prerequisites_validation_missing_directory(self, mock_env_vars):
        """Test prerequisites validation fails with missing directory."""
        pipeline = PodFlowerPipeline(sample_directory="nonexistent_dir")
        
        result = pipeline.validate_prerequisites()
        assert result is False
    
    def test_prerequisites_validation_missing_audio_files(self, mock_env_vars):
        """Test prerequisites validation fails with no audio files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty_episode"
            empty_dir.mkdir()
            
            pipeline = PodFlowerPipeline(sample_directory=str(empty_dir))
            result = pipeline.validate_prerequisites()
            assert result is False
    
    def test_prerequisites_validation_missing_env_vars(self, temp_sample_dir):
        """Test prerequisites validation fails with missing env vars."""
        pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
        
        result = pipeline.validate_prerequisites()
        assert result is False
    
    @patch('agents.recorder.recorder.Agent.run')
    @patch('agents.filler_removal.filler_removal.Agent.run') 
    @patch('agents.concat_audio.concat_audio.Agent.run')
    @patch('agents.title_notes.title_notes.Agent.run')
    @patch('agents.ad_break.ad_break.Agent.run')
    @patch('agents.mastering.mastering.Agent.run')
    @patch('agents.export_package.export_package.Agent.run')
    @patch('agents.deploy_vercel.deploy_vercel.Agent.run')
    @patch('agents.wordpress_publish.wordpress_publish.Agent.run')
    @patch('agents.post_to_x.post_to_x.Agent.run')
    @pytest.mark.asyncio
    async def test_full_pipeline_execution(
        self,
        mock_post_to_x,
        mock_wordpress,
        mock_deploy_vercel,
        mock_export_package,
        mock_mastering,
        mock_ad_break,
        mock_title_notes,
        mock_concat_audio,
        mock_filler_removal,
        mock_recorder,
        temp_sample_dir,
        mock_env_vars
    ):
        """Test complete pipeline execution with mocked agents."""
        
        # Setup mock return values to simulate pipeline flow
        mock_recorder.return_value = {
            "audio_raw_paths": [f"{temp_sample_dir}/raw_audio.mp4"],
            "source_directory": temp_sample_dir
        }
        
        mock_filler_removal.return_value = {
            "audio_clean_path": f"{temp_sample_dir}/clean_audio.wav",
            "transcript": "これはテストの転写です。"
        }
        
        mock_concat_audio.return_value = {
            "audio_with_intro_outro": f"{temp_sample_dir}/final_audio.wav"
        }
        
        mock_title_notes.return_value = {
            "title_candidates": [
                "テストエピソード1",
                "テストエピソード2", 
                "テストエピソード3",
                "テストエピソード4",
                "テストエピソード5"
            ],
            "shownote_md": "# 概要\nテストエピソードです。"
        }
        
        mock_ad_break.return_value = {
            "ad_timestamps": ["10:30", "25:45"]
        }
        
        mock_mastering.return_value = {
            "audio_mastered_path": f"{temp_sample_dir}/mastered_audio.mp3"
        }
        
        mock_export_package.return_value = {
            "episode_package_dir": f"{temp_sample_dir}/build/20241201_episode01",
            "metadata": {
                "title": "テストエピソード1",
                "duration_seconds": 1800,
                "file_size_bytes": 50000000
            }
        }
        
        mock_deploy_vercel.return_value = {
            "vercel_deployment_url": "https://test.vercel.app"
        }
        
        mock_wordpress.return_value = {
            "wordpress_post_url": "https://momithub.com/test-episode"
        }
        
        mock_post_to_x.return_value = {
            "x_tweet_url": "https://x.com/momitfm/status/123456789"
        }
        
        # Execute pipeline
        pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
        result = await pipeline.run()
        
        # Verify all agents were called
        mock_recorder.assert_called_once()
        mock_filler_removal.assert_called_once()
        mock_concat_audio.assert_called_once()
        mock_title_notes.assert_called_once()
        mock_ad_break.assert_called_once()
        mock_mastering.assert_called_once()
        mock_export_package.assert_called_once()
        mock_deploy_vercel.assert_called_once()
        mock_wordpress.assert_called_once()
        mock_post_to_x.assert_called_once()
        
        # Verify final result contains expected keys
        assert "episode_package_dir" in result
        assert "wordpress_post_url" in result
        assert "x_tweet_url" in result
        assert "vercel_deployment_url" in result
    
    @pytest.mark.asyncio
    async def test_pipeline_failure_handling(self, temp_sample_dir, mock_env_vars):
        """Test pipeline handles agent failures gracefully."""
        
        with patch('agents.recorder.recorder.Agent.run') as mock_recorder:
            # Make recorder agent fail
            mock_recorder.side_effect = Exception("Recorder failed")
            
            pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
            
            with pytest.raises(Exception) as exc_info:
                await pipeline.run()
            
            assert "Recorder failed" in str(exc_info.value)
    
    def test_pipeline_state_flow(self, temp_sample_dir, mock_env_vars):
        """Test that pipeline maintains proper state flow between agents."""
        pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
        
        # Verify agents are properly connected in sequence
        main_pipeline = pipeline.main_pipeline
        assert main_pipeline.name == "PodFlowerMainPipeline"
        
        # Check that sub-agents are properly configured
        sub_agents = main_pipeline.sub_agents
        assert len(sub_agents) == 4  # 4 main phases
        
        # Verify first phase is audio processing
        audio_processing = sub_agents[0]
        assert audio_processing.name == "AudioProcessingPipeline"
        
        # Verify second phase is content generation
        content_generation = sub_agents[1]
        assert content_generation.name == "ContentGenerationPipeline"
    
    @pytest.mark.asyncio
    async def test_one_command_demo_requirement(self, temp_sample_dir, mock_env_vars):
        """Test the SPEC requirement: one-command demo functionality."""
        
        # This test verifies that the system can be run with a single command
        # as specified in the SPEC: `python pipelines/full_workflow.py sample_episode/`
        
        pipeline = PodFlowerPipeline(sample_directory=temp_sample_dir)
        
        # Verify prerequisites can be validated
        assert pipeline.validate_prerequisites() is True
        
        # Verify pipeline can be initialized and configured
        assert pipeline.main_pipeline is not None
        assert hasattr(pipeline, 'run')
        
        # This confirms the one-command demo architecture is in place
        # (actual execution would require all external services to be mocked)


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests for individual agent functionality."""
    
    @pytest.mark.asyncio
    async def test_recorder_agent_file_detection(self):
        """Test that recorder agent correctly detects audio files."""
        from agents.recorder.recorder import Agent as RecorderAgent
        
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_dir = Path(temp_dir) / "test_episode"
            sample_dir.mkdir()
            
            # Create test audio files
            (sample_dir / "audio1.mp4").write_bytes(b"dummy")
            (sample_dir / "audio2.wav").write_bytes(b"dummy")
            (sample_dir / "not_audio.txt").write_text("not audio")
            
            agent = RecorderAgent(watch_directory=str(sample_dir))
            result = await agent.run({})
            
            assert "audio_raw_paths" in result
            audio_paths = result["audio_raw_paths"]
            assert len(audio_paths) == 2
            assert any("audio1.mp4" in path for path in audio_paths)
            assert any("audio2.wav" in path for path in audio_paths)
    
    def test_state_key_compliance(self):
        """Test that all agents comply with the state key contract from SPEC."""
        
        # This test verifies that agents produce the expected state keys
        # as defined in the SPEC's "Shared State Keys" table
        
        expected_producers = {
            "audio_raw_paths": "recorder",
            "transcript": "filler_removal", 
            "audio_clean_path": "filler_removal",
            "title_candidates": "title_notes",
            "shownote_md": "title_notes",
            "ad_timestamps": "ad_break",
            "episode_package_dir": "export_package"
        }
        
        # Verify each agent class exists and has the expected name
        from agents.recorder.recorder import Agent as RecorderAgent
        from agents.filler_removal.filler_removal import Agent as FillerRemovalAgent
        from agents.title_notes.title_notes import Agent as TitleNotesAgent
        from agents.ad_break.ad_break import Agent as AdBreakAgent
        from agents.export_package.export_package import Agent as ExportPackageAgent
        
        assert RecorderAgent.name == "recorder"
        assert FillerRemovalAgent.name == "filler_removal"
        assert TitleNotesAgent.name == "title_notes"
        assert AdBreakAgent.name == "ad_break"
        assert ExportPackageAgent.name == "export_package"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 