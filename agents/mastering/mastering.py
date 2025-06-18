"""Mastering Agent - Loudness & peak normalization."""

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
    """Mastering Agent - see SPEC.md for full contract."""
    
    name = "mastering"
    description = "Normalize loudness to -16 LUFS and peak to -1 dB"
    version = "0.1.0"
    
    async def run(self, state: Dict) -> Dict:
        """Apply audio mastering with loudness normalization.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with mastered audio path.
        """
        logger.info("Starting audio mastering agent")
        
        # Get input audio (either concatenated or clean audio)
        input_audio = state.get("audio_with_intro_outro") or state.get("audio_clean_path")
        if not input_audio:
            raise AgentError("No input audio found in state")
            
        logger.info("Processing audio for mastering", input_file=input_audio)
        
        # Generate output path
        input_path = Path(input_audio)
        output_path = input_path.parent / f"{input_path.stem}_mastered{input_path.suffix}"
        
        try:
            # Apply loudness normalization using ffmpeg loudnorm filter
            # Target: -16 LUFS integrated loudness, -1 dB peak
            (
                ffmpeg
                .input(input_audio)
                .filter('loudnorm', 
                       I=-16.0,    # Integrated loudness target (LUFS)
                       TP=-1.0,    # True peak target (dBFS)
                       LRA=11,     # Loudness range target (LU)
                       measured_I=None,  # Let ffmpeg measure
                       measured_LRA=None,
                       measured_TP=None,
                       measured_thresh=None,
                       offset=None,
                       linear=True,
                       print_format='summary')
                .output(str(output_path))
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info("Audio mastering completed",
                       input=input_audio,
                       output=str(output_path),
                       target_lufs=-16.0,
                       target_peak=-1.0)
            
            return {
                "audio_mastered_path": str(output_path)
            }
            
        except Exception as e:
            raise AgentError(f"Failed to master audio: {e}") 