"""Ad-Break Detector Agent - Detect topic-shift ad points."""

import math
from typing import Dict, List, Tuple
import structlog
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from google.adk.agents import BaseAgent

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """Ad Break Detector Agent - see SPEC.md for full contract."""
    
    name = "ad_break"
    description = "Detect topic-shift points for ad placement using semantic similarity"
    version = "0.1.0"
    
    def __init__(self):
        super().__init__()
        # Load multilingual sentence transformer for Japanese text
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
    async def run(self, state: Dict) -> Dict:
        """Detect ad break points based on topic shifts.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with ad break timestamps.
        """
        logger.info("Starting ad break detection")
        
        transcript = state.get("transcript")
        audio_clean_path = state.get("audio_clean_path")
        
        if not transcript:
            raise AgentError("No transcript found in state")
        if not audio_clean_path:
            raise AgentError("No clean audio path found in state")
            
        # Get audio duration for validation
        audio_duration = await self._get_audio_duration(audio_clean_path)
        logger.info("Audio duration detected", duration_seconds=audio_duration)
        
        # Split transcript into 30-second windows
        text_windows = self._create_text_windows(transcript, window_seconds=30)
        
        if len(text_windows) < 2:
            logger.warning("Not enough text windows for ad break detection")
            return {"ad_timestamps": []}
        
        # Generate embeddings for each window
        embeddings = self._generate_embeddings(text_windows)
        
        # Detect topic shifts using cosine similarity
        topic_shifts = self._detect_topic_shifts(embeddings, similarity_threshold=0.3)
        
        # Convert to timestamps and apply rules
        ad_timestamps = self._apply_ad_rules(topic_shifts, audio_duration)
        
        logger.info("Ad break detection completed", 
                   potential_breaks=len(topic_shifts),
                   final_breaks=len(ad_timestamps))
        
        return {
            "ad_timestamps": ad_timestamps,
            "topic_shifts": topic_shifts
        }
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            import ffmpeg
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            raise AgentError(f"Failed to get audio duration: {e}")
    
    def _create_text_windows(self, transcript: str, window_seconds: int = 30) -> List[Dict]:
        """Split transcript into time-based windows."""
        # Split transcript into sentences
        sentences = transcript.split('。')  # Japanese sentence delimiter
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Estimate timing (rough approximation: ~150 characters per 30 seconds in Japanese)
        chars_per_window = 150 * window_seconds / 30
        
        windows = []
        current_window = ""
        current_time = 0
        
        for sentence in sentences:
            if len(current_window + sentence) > chars_per_window and current_window:
                # Start new window
                windows.append({
                    'text': current_window.strip(),
                    'start_time': current_time,
                    'end_time': current_time + window_seconds
                })
                current_window = sentence
                current_time += window_seconds
            else:
                current_window += sentence + "。"
        
        # Add final window
        if current_window.strip():
            windows.append({
                'text': current_window.strip(),
                'start_time': current_time,
                'end_time': current_time + window_seconds
            })
        
        logger.info("Created text windows", count=len(windows))
        return windows
    
    def _generate_embeddings(self, text_windows: List[Dict]) -> np.ndarray:
        """Generate embeddings for text windows."""
        texts = [window['text'] for window in text_windows]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        logger.info("Generated embeddings", shape=embeddings.shape)
        return embeddings
    
    def _detect_topic_shifts(self, embeddings: np.ndarray, similarity_threshold: float = 0.3) -> List[int]:
        """Detect topic shifts by comparing consecutive embeddings."""
        topic_shifts = []
        
        for i in range(len(embeddings) - 1):
            # Calculate cosine similarity between consecutive windows
            similarity = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            
            # Lower similarity indicates topic shift
            if similarity < (1 - similarity_threshold):
                topic_shifts.append(i + 1)  # Shift happens at start of next window
                logger.debug("Topic shift detected", 
                           window_index=i + 1, 
                           similarity=similarity)
        
        return topic_shifts
    
    def _apply_ad_rules(self, topic_shifts: List[int], audio_duration: float) -> List[str]:
        """Apply ad placement rules and convert to timestamps."""
        ad_timestamps = []
        
        # Rules from SPEC:
        # - Earliest ad ≥ 00:10:00 (600 seconds)
        # - Latest ad ≤ 00:45:00 (2700 seconds)
        MIN_AD_TIME = 600   # 10 minutes
        MAX_AD_TIME = 2700  # 45 minutes
        
        for window_index in topic_shifts:
            # Convert window index to approximate timestamp (30-second windows)
            timestamp_seconds = window_index * 30
            
            # Apply time rules
            if MIN_AD_TIME <= timestamp_seconds <= min(MAX_AD_TIME, audio_duration - 60):
                # Format as MM:SS
                minutes = int(timestamp_seconds // 60)
                seconds = int(timestamp_seconds % 60)
                timestamp_str = f"{minutes:02d}:{seconds:02d}"
                ad_timestamps.append(timestamp_str)
        
        # Limit to maximum of 3 ad breaks
        ad_timestamps = ad_timestamps[:3]
        
        return ad_timestamps 