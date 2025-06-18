"""
Unit Tests for Individual PodFlower Agents

Tests each agent's functionality in isolation with mocked dependencies.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRecorderAgent:
    """Unit tests for Recorder Agent."""
    
    @pytest.mark.asyncio
    async def test_detects_audio_files(self):
        """Test that recorder agent detects supported audio formats."""
        from agents.recorder.recorder import Agent as RecorderAgent
        
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_dir = Path(temp_dir)
            
            # Create test files
            (sample_dir / "episode.mp4").write_bytes(b"mp4 content")
            (sample_dir / "backup.wav").write_bytes(b"wav content")
            (sample_dir / "notes.txt").write_text("not audio")
            
            agent = RecorderAgent(watch_directory=str(sample_dir))
            result = await agent.run({})
            
            assert "audio_raw_paths" in result
            paths = result["audio_raw_paths"]
            assert len(paths) == 2
            assert any("episode.mp4" in p for p in paths)
            assert any("backup.wav" in p for p in paths)
    
    @pytest.mark.asyncio
    async def test_fails_with_missing_directory(self):
        """Test that recorder agent fails gracefully with missing directory."""
        from agents.recorder.recorder import Agent as RecorderAgent, AgentError
        
        agent = RecorderAgent(watch_directory="nonexistent_dir")
        
        with pytest.raises(AgentError, match="Watch directory does not exist"):
            await agent.run({})
    
    @pytest.mark.asyncio
    async def test_fails_with_no_audio_files(self):
        """Test that recorder agent fails when no audio files found."""
        from agents.recorder.recorder import Agent as RecorderAgent, AgentError
        
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = RecorderAgent(watch_directory=temp_dir)
            
            with pytest.raises(AgentError, match="No new audio files found"):
                await agent.run({})


class TestTitleNotesAgent:
    """Unit tests for Title Notes Agent."""
    
    @pytest.mark.asyncio
    async def test_generates_titles_and_notes(self):
        """Test that title notes agent generates proper output format."""
        from agents.title_notes.title_notes import Agent as TitleNotesAgent
        
        agent = TitleNotesAgent()
        
        # Mock the LLM response
        with patch.object(agent, 'generate_content') as mock_generate:
            mock_generate.return_value = """{
                "title_candidates": [
                    "テストタイトル1",
                    "テストタイトル2", 
                    "テストタイトル3",
                    "テストタイトル4",
                    "テストタイトル5"
                ],
                "shownote_md": "# 概要\\nテスト番組です。\\n\\n# 主なトピック\\n- トピック1\\n- トピック2"
            }"""
            
            state = {"transcript": "テストの転写内容です。"}
            result = await agent.run(state)
            
            assert "title_candidates" in result
            assert "shownote_md" in result
            assert len(result["title_candidates"]) == 5
            assert "# 概要" in result["shownote_md"]
    
    @pytest.mark.asyncio
    async def test_validates_response_schema(self):
        """Test that title notes agent validates LLM response schema."""
        from agents.title_notes.title_notes import Agent as TitleNotesAgent
        
        agent = TitleNotesAgent()
        
        # Test invalid schema validation
        invalid_responses = [
            {"title_candidates": ["only", "four", "titles", "here"]},  # Not 5 titles
            {"shownote_md": "Notes without title_candidates"},  # Missing key
            {"title_candidates": [1, 2, 3, 4, 5], "shownote_md": "Invalid titles"},  # Wrong type
        ]
        
        for invalid_response in invalid_responses:
            assert agent._validate_response(invalid_response) is False
        
        # Test valid schema
        valid_response = {
            "title_candidates": ["1", "2", "3", "4", "5"],
            "shownote_md": "# 概要\nValid content\n# 主なトピック\nMore content"
        }
        assert agent._validate_response(valid_response) is True


class TestAdBreakAgent:
    """Unit tests for Ad Break Agent."""
    
    @pytest.mark.asyncio
    async def test_detects_topic_shifts(self):
        """Test that ad break agent detects topic shifts in transcript."""
        from agents.ad_break.ad_break import Agent as AdBreakAgent
        
        # Mock the sentence transformer model
        with patch('agents.ad_break.ad_break.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_transformer.return_value = mock_model
            
            # Mock embeddings that show topic shift
            import numpy as np
            mock_embeddings = np.array([
                [1.0, 0.0, 0.0],  # Topic A
                [1.0, 0.0, 0.0],  # Topic A 
                [0.0, 1.0, 0.0],  # Topic B (shift)
                [0.0, 1.0, 0.0],  # Topic B
            ])
            mock_model.encode.return_value = mock_embeddings
            
            agent = AdBreakAgent()
            
            # Mock audio duration
            with patch.object(agent, '_get_audio_duration') as mock_duration:
                mock_duration.return_value = 3600  # 1 hour
                
                state = {
                    "transcript": "最初のトピック。" * 20 + "二番目のトピック。" * 20,
                    "audio_clean_path": "test_audio.wav"
                }
                
                result = await agent.run(state)
                
                assert "ad_timestamps" in result
                assert "topic_shifts" in result
    
    def test_applies_ad_rules(self):
        """Test that ad break agent applies time-based rules correctly."""
        from agents.ad_break.ad_break import Agent as AdBreakAgent
        
        agent = AdBreakAgent()
        
        # Test with topic shifts at various times
        topic_shifts = [5, 20, 50, 100]  # Windows (30-second each)
        audio_duration = 3600  # 1 hour
        
        ad_timestamps = agent._apply_ad_rules(topic_shifts, audio_duration)
        
        # Should only include shifts between 10:00 and 45:00
        # Window 20 = 10:00, Window 50 = 25:00 
        assert len(ad_timestamps) >= 1
        for timestamp in ad_timestamps:
            minutes, seconds = map(int, timestamp.split(':'))
            total_seconds = minutes * 60 + seconds
            assert 600 <= total_seconds <= 2700  # 10 min to 45 min


class TestMasteringAgent:
    """Unit tests for Mastering Agent."""
    
    @pytest.mark.asyncio
    async def test_masters_audio_with_correct_parameters(self):
        """Test that mastering agent applies correct audio processing."""
        from agents.mastering.mastering import Agent as MasteringAgent
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "input_audio.wav"
            input_file.write_bytes(b"dummy audio content")
            
            agent = MasteringAgent()
            
            # Mock ffmpeg processing
            with patch('agents.mastering.mastering.ffmpeg') as mock_ffmpeg:
                mock_input = Mock()
                mock_ffmpeg.input.return_value = mock_input
                mock_filter = Mock()
                mock_input.filter.return_value = mock_filter
                mock_output = Mock()
                mock_filter.output.return_value = mock_output
                mock_overwrite = Mock()
                mock_output.overwrite_output.return_value = mock_overwrite
                mock_overwrite.run.return_value = None
                
                state = {"audio_clean_path": str(input_file)}
                result = await agent.run(state)
                
                # Verify ffmpeg was called with correct parameters
                mock_input.filter.assert_called_once_with(
                    'loudnorm',
                    I=-16.0,    # Target LUFS from SPEC
                    TP=-1.0,    # Target peak from SPEC
                    LRA=11,
                    measured_I=None,
                    measured_LRA=None,
                    measured_TP=None,
                    measured_thresh=None,
                    offset=None,
                    linear=True,
                    print_format='summary'
                )
                
                assert "audio_mastered_path" in result


class TestExportPackageAgent:
    """Unit tests for Export Package Agent."""
    
    @pytest.mark.asyncio
    async def test_creates_episode_package(self):
        """Test that export package agent creates proper episode structure."""
        from agents.export_package.export_package import Agent as ExportPackageAgent
        
        with tempfile.TemporaryDirectory() as temp_dir:
            build_dir = Path(temp_dir) / "build"
            
            agent = ExportPackageAgent(build_dir=str(build_dir))
            
            # Mock audio metadata
            with patch.object(agent, '_get_audio_metadata') as mock_metadata:
                mock_metadata.return_value = (1800.0, 50000000)  # 30 min, 50MB
                
                # Mock checksum
                with patch.object(agent, '_generate_checksum') as mock_checksum:
                    mock_checksum.return_value = "abc123def456"
                    
                    # Create dummy mastered audio
                    mastered_audio = Path(temp_dir) / "mastered.mp3"
                    mastered_audio.write_bytes(b"mastered audio content")
                    
                    state = {
                        "audio_mastered_path": str(mastered_audio),
                        "title_candidates": ["タイトル1", "タイトル2", "タイトル3", "タイトル4", "タイトル5"],
                        "shownote_md": "# 概要\nテスト番組",
                        "ad_timestamps": ["15:30", "32:15"]
                    }
                    
                    result = await agent.run(state)
                    
                    assert "episode_package_dir" in result
                    assert "metadata" in result
                    
                    # Verify package directory was created
                    package_dir = Path(result["episode_package_dir"])
                    assert package_dir.exists()
                    
                    # Verify required files exist
                    assert (package_dir / "episode_final.mp3").exists()
                    assert (package_dir / "shownote.md").exists()
                    assert (package_dir / "meta.json").exists()
                    
                    # Verify metadata structure
                    metadata = result["metadata"]
                    assert metadata["title"] == "タイトル1"
                    assert metadata["duration_seconds"] == 1800.0
                    assert len(metadata["title_candidates"]) == 5


class TestAgentErrorHandling:
    """Test error handling across all agents."""
    
    @pytest.mark.asyncio
    async def test_agents_raise_agent_error_on_failure(self):
        """Test that agents raise AgentError for recoverable failures."""
        from agents.recorder.recorder import Agent as RecorderAgent, AgentError
        
        # Test with invalid directory
        agent = RecorderAgent(watch_directory="invalid_path")
        
        with pytest.raises(AgentError):
            await agent.run({})
    
    def test_all_agents_have_required_metadata(self):
        """Test that all agents have required name, description, version."""
        agent_modules = [
            'agents.recorder.recorder',
            'agents.filler_removal.filler_removal',
            'agents.concat_audio.concat_audio',
            'agents.title_notes.title_notes',
            'agents.ad_break.ad_break',
            'agents.mastering.mastering',
            'agents.export_package.export_package',
            'agents.deploy_vercel.deploy_vercel',
            'agents.wordpress_publish.wordpress_publish',
            'agents.post_to_x.post_to_x'
        ]
        
        for module_path in agent_modules:
            module = __import__(module_path, fromlist=['Agent'])
            agent_class = getattr(module, 'Agent')
            
            assert hasattr(agent_class, 'name')
            assert hasattr(agent_class, 'description')
            assert hasattr(agent_class, 'version')
            assert agent_class.name is not None
            assert agent_class.description is not None
            assert agent_class.version == "0.1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 