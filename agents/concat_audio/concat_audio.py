"""Concat Audio Agent - Prepend/append intro & outro."""

import os
from pathlib import Path
from typing import Dict
import structlog
from google.adk.agents import BaseAgent
import ffmpeg

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """Concat Audio Agent - see SPEC.md for full contract."""
    
    name = "concat_audio"
    description = "Prepend intro.mp3 and append outro.mp3 to clean audio"
    version = "0.1.0"
    
    def __init__(self, assets_dir: str = "assets/"):
        super().__init__()
        self.assets_dir = Path(assets_dir)
        
    async def run(self, state: Dict) -> Dict:
        """Prepend intro and append outro to clean audio.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with concatenated audio path.
        """
        logger.info("Starting audio concatenation agent")
        
        audio_clean_path = state.get("audio_clean_path")
        if not audio_clean_path:
            raise AgentError("No clean audio path found in state")
            
        # Check for required assets
        intro_path = self.assets_dir / "intro.mp3"
        outro_path = self.assets_dir / "outro.mp3"
        
        if not intro_path.exists():
            raise AgentError(f"Intro file missing: {intro_path}")
        if not outro_path.exists():
            raise AgentError(f"Outro file missing: {outro_path}")
            
        logger.info("Found required assets", intro=str(intro_path), outro=str(outro_path))
        
        # Generate output path
        clean_path = Path(audio_clean_path)
        output_path = clean_path.parent / f"{clean_path.stem}_with_intro_outro{clean_path.suffix}"
        
        try:
            # Create concatenation using ffmpeg concat demuxer
            concat_file = self._create_concat_file(intro_path, audio_clean_path, outro_path)
            
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(str(output_path), c='copy')
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Clean up temporary concat file
            os.unlink(concat_file)
            
            logger.info("Audio concatenation completed", 
                       input=audio_clean_path,
                       output=str(output_path))
            
            return {
                "audio_with_intro_outro": str(output_path)
            }
            
        except Exception as e:
            raise AgentError(f"Failed to concatenate audio: {e}")
    
    def _create_concat_file(self, intro_path: Path, main_path: str, outro_path: Path) -> str:
        """Create temporary concat file for ffmpeg."""
        import tempfile
        
        concat_fd, concat_file = tempfile.mkstemp(suffix='.txt', text=True)
        
        try:
            with os.fdopen(concat_fd, 'w') as f:
                f.write(f"file '{intro_path.absolute()}'\n")
                f.write(f"file '{Path(main_path).absolute()}'\n")
                f.write(f"file '{outro_path.absolute()}'\n")
            
            return concat_file
            
        except Exception:
            os.close(concat_fd)
            raise 