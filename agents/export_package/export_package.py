"""Export Package Agent - Bundle final audio + metadata."""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, ClassVar
import structlog
from google.adk.agents import BaseAgent
import ffmpeg

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """Export Package Agent - see SPEC.md for full contract."""
    name: str = "export_package"
    description: str = "Create final episode package with audio, metadata, and show notes"
    version: str = "0.1.0"
    
    def __init__(self, build_dir: str = "build/", **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'build_dir', Path(build_dir))
        
    async def run(self, state: Dict) -> Dict:
        """Create final episode package.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with episode package directory.
        """
        logger.info("Starting episode package export")
        
        # Get required inputs
        mastered_audio = state.get("audio_mastered_path")
        title_candidates = state.get("title_candidates", [])
        shownote_md = state.get("shownote_md", "")
        ad_timestamps = state.get("ad_timestamps", [])
        
        if not mastered_audio:
            raise AgentError("No mastered audio found in state")
        if not title_candidates:
            raise AgentError("No title candidates found in state")
            
        # Create episode directory
        episode_dir = self._create_episode_directory()
        logger.info("Created episode directory", path=str(episode_dir))
        
        try:
            # 1. Copy and rename final audio
            final_audio_path = self._copy_final_audio(mastered_audio, episode_dir)
            
            # 2. Get audio metadata
            duration, file_size = await self._get_audio_metadata(final_audio_path)
            
            # 3. Generate SHA256 checksum
            checksum = self._generate_checksum(final_audio_path)
            
            # 4. Create show notes file
            shownotes_path = self._create_shownotes_file(shownote_md, episode_dir)
            
            # 5. Create metadata JSON
            metadata = {
                "title": title_candidates[0],  # Use first title as selected
                "title_candidates": title_candidates,
                "duration_seconds": duration,
                "file_size_bytes": file_size,
                "sha256_checksum": checksum,
                "ad_timestamps": ad_timestamps,
                "created_at": datetime.now().isoformat(),
                "format": "mp3",
                "sample_rate": 44100,
                "channels": 2
            }
            
            metadata_path = self._create_metadata_file(metadata, episode_dir)
            
            logger.info("Episode package created successfully",
                       directory=str(episode_dir),
                       audio_duration=duration,
                       file_size=file_size,
                       title=metadata["title"])
            
            return {
                "episode_package_dir": str(episode_dir),
                "final_audio_path": str(final_audio_path),
                "metadata": metadata,
                "shownotes_path": str(shownotes_path)
            }
            
        except Exception as e:
            raise AgentError(f"Failed to create episode package: {e}")
    
    def _create_episode_directory(self) -> Path:
        """Create timestamped episode directory."""
        # Format: YYYYMMDD_episodeNN
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Find next episode number for today
        episode_num = 1
        while True:
            episode_dir = self.build_dir / f"{date_str}_episode{episode_num:02d}"
            if not episode_dir.exists():
                break
            episode_num += 1
        
        # Create directory
        episode_dir.mkdir(parents=True, exist_ok=True)
        return episode_dir
    
    def _copy_final_audio(self, source_path: str, episode_dir: Path) -> Path:
        """Copy mastered audio to final location."""
        import shutil
        
        final_audio_path = episode_dir / "episode_final.mp3"
        
        # Convert to MP3 if not already
        source_ext = Path(source_path).suffix.lower()
        if source_ext != '.mp3':
            # Convert to MP3
            (
                ffmpeg
                .input(source_path)
                .output(str(final_audio_path), 
                       acodec='mp3',
                       audio_bitrate='192k',
                       ar=44100,
                       ac=2)
                .overwrite_output()
                .run(quiet=True)
            )
        else:
            # Direct copy
            shutil.copy2(source_path, final_audio_path)
        
        return final_audio_path
    
    async def _get_audio_metadata(self, audio_path: Path) -> tuple[float, int]:
        """Get audio duration and file size."""
        try:
            # Get duration using ffprobe
            probe = ffmpeg.probe(str(audio_path))
            duration = float(probe['streams'][0]['duration'])
            
            # Get file size
            file_size = audio_path.stat().st_size
            
            return duration, file_size
            
        except Exception as e:
            raise AgentError(f"Failed to get audio metadata: {e}")
    
    def _generate_checksum(self, file_path: Path) -> str:
        """Generate SHA256 checksum for the audio file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def _create_shownotes_file(self, shownote_md: str, episode_dir: Path) -> Path:
        """Create markdown show notes file."""
        shownotes_path = episode_dir / "shownote.md"
        
        with open(shownotes_path, 'w', encoding='utf-8') as f:
            f.write(shownote_md)
        
        return shownotes_path
    
    def _create_metadata_file(self, metadata: Dict, episode_dir: Path) -> Path:
        """Create JSON metadata file."""
        metadata_path = episode_dir / "meta.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return metadata_path 