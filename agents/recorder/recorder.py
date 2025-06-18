"""Recorder Agent - Watch folder / poll raw tracks."""

import os
import asyncio
from pathlib import Path
from typing import Dict, List
import structlog
from google.adk.agents import BaseAgent

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """Recorder Agent - see SPEC.md for full contract."""
    
    name = "recorder"
    description = "Watch folder and detect new Zoom/Riverside raw tracks"
    version = "0.1.0"
    
    def __init__(self, watch_directory: str = "sample_episode/"):
        super().__init__()
        self.watch_directory = Path(watch_directory)
        self.processed_files = set()
        
    async def run(self, state: Dict) -> Dict:
        """Watch directory for new audio tracks and add to state.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice to merge back into global state.
        """
        logger.info("Starting recorder agent", directory=str(self.watch_directory))
        
        if not self.watch_directory.exists():
            raise AgentError(f"Watch directory does not exist: {self.watch_directory}")
            
        # Find raw audio files (Zoom/Riverside formats)
        audio_extensions = {'.mp4', '.wav', '.m4a', '.mp3'}
        raw_audio_files = []
        
        for file_path in self.watch_directory.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() in audio_extensions and
                str(file_path) not in self.processed_files):
                
                raw_audio_files.append(str(file_path))
                self.processed_files.add(str(file_path))
                logger.info("Found new audio file", file=str(file_path))
                
        if not raw_audio_files:
            raise AgentError("No new audio files found in watch directory")
            
        return {
            "audio_raw_paths": raw_audio_files,
            "source_directory": str(self.watch_directory)
        } 