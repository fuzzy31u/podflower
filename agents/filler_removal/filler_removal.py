"""Filler Removal Agent - STT + cut Japanese filler words."""

import os
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import structlog
from google.cloud import speech
from google.adk.agents import BaseAgent
import ffmpeg

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """Filler Removal Agent - see SPEC.md for full contract."""
    
    name = "filler_removal"
    description = "Remove Japanese filler words using Google Cloud Speech-to-Text v2"
    version = "0.1.0"
    
    # Japanese filler words to remove
    FILLER_WORDS = {
        "えーと", "あのー", "まあ", "その", "なんか", 
        "そのー", "あー", "えー", "うーん", "でも"
    }
    
    def __init__(self):
        super().__init__()
        self.speech_client = speech.SpeechClient()
        
    async def run(self, state: Dict) -> Dict:
        """Remove filler words from Japanese audio using STT.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with clean audio and transcript.
        """
        logger.info("Starting filler removal agent")
        
        audio_raw_paths = state.get("audio_raw_paths", [])
        if not audio_raw_paths:
            raise AgentError("No raw audio paths found in state")
            
        # Process the first audio file (main track)
        main_audio_path = audio_raw_paths[0]
        logger.info("Processing main audio track", file=main_audio_path)
        
        # Step 1: Convert to appropriate format for Speech-to-Text
        wav_path = await self._convert_to_wav(main_audio_path)
        
        # Step 2: Perform speech-to-text with timestamps
        transcript_with_timestamps = await self._transcribe_with_timestamps(wav_path)
        
        # Step 3: Identify filler word segments
        cut_list = self._identify_filler_segments(transcript_with_timestamps)
        
        # Step 4: Apply cuts using ffmpeg
        clean_audio_path = await self._apply_cuts(wav_path, cut_list)
        
        # Step 5: Generate clean transcript
        clean_transcript = self._generate_clean_transcript(transcript_with_timestamps, cut_list)
        
        logger.info("Filler removal completed", 
                   original_file=main_audio_path,
                   clean_file=clean_audio_path,
                   filler_segments_removed=len(cut_list))
        
        return {
            "audio_clean_path": clean_audio_path,
            "transcript": clean_transcript,
            "filler_cuts": cut_list,
            "original_transcript": transcript_with_timestamps
        }
    
    async def _convert_to_wav(self, input_path: str) -> str:
        """Convert input audio to WAV format for Speech-to-Text."""
        output_path = input_path.replace(Path(input_path).suffix, "_converted.wav")
        
        try:
            (
                ffmpeg
                .input(input_path)
                .output(output_path, 
                       acodec='pcm_s16le',
                       ac=1,  # mono
                       ar=16000)  # 16kHz sample rate
                .overwrite_output()
                .run(quiet=True)
            )
            logger.info("Audio converted to WAV", input=input_path, output=output_path)
            return output_path
        except Exception as e:
            raise AgentError(f"Failed to convert audio to WAV: {e}")
    
    async def _transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """Transcribe audio with word-level timestamps."""
        try:
            with open(audio_path, 'rb') as audio_file:
                content = audio_file.read()
            
            # Configure recognition request
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="ja-JP",
                enable_word_time_offsets=True,
                enable_automatic_punctuation=True,
                model="latest_long"
            )
            
            audio = speech.RecognitionAudio(content=content)
            
            # Perform synchronous recognition
            response = self.speech_client.recognize(config=config, audio=audio)
            
            # Extract words with timestamps
            words_with_timestamps = []
            for result in response.results:
                for word_info in result.alternatives[0].words:
                    words_with_timestamps.append({
                        'word': word_info.word,
                        'start_time': word_info.start_time.total_seconds(),
                        'end_time': word_info.end_time.total_seconds()
                    })
            
            logger.info("Transcription completed", total_words=len(words_with_timestamps))
            return words_with_timestamps
            
        except Exception as e:
            raise AgentError(f"Failed to transcribe audio: {e}")
    
    def _identify_filler_segments(self, transcript_with_timestamps: List[Dict]) -> List[Tuple[float, float]]:
        """Identify time segments containing filler words."""
        cut_segments = []
        
        for word_info in transcript_with_timestamps:
            word = word_info['word'].strip()
            if word in self.FILLER_WORDS:
                cut_segments.append((word_info['start_time'], word_info['end_time']))
                logger.debug("Filler word detected", 
                           word=word, 
                           start=word_info['start_time'], 
                           end=word_info['end_time'])
        
        # Merge overlapping/adjacent segments
        if cut_segments:
            cut_segments.sort()
            merged_segments = [cut_segments[0]]
            
            for current_start, current_end in cut_segments[1:]:
                last_start, last_end = merged_segments[-1]
                if current_start <= last_end + 0.1:  # 100ms tolerance
                    merged_segments[-1] = (last_start, max(last_end, current_end))
                else:
                    merged_segments.append((current_start, current_end))
            
            return merged_segments
        
        return []
    
    async def _apply_cuts(self, input_path: str, cut_list: List[Tuple[float, float]]) -> str:
        """Apply cuts to remove filler segments using ffmpeg."""
        if not cut_list:
            # No cuts needed, just copy the file
            output_path = input_path.replace("_converted.wav", "_clean.wav")
            import shutil
            shutil.copy2(input_path, output_path)
            return output_path
        
        output_path = input_path.replace("_converted.wav", "_clean.wav")
        
        try:
            # Create filter complex for removing segments
            filter_parts = []
            last_end = 0
            segment_index = 0
            
            for start_time, end_time in cut_list:
                if last_end < start_time:
                    # Add segment before the cut
                    filter_parts.append(f"[0:a]atrim=start={last_end}:end={start_time},asetpts=PTS-STARTPTS[a{segment_index}];")
                    segment_index += 1
                last_end = end_time
            
            # Add final segment after last cut
            filter_parts.append(f"[0:a]atrim=start={last_end},asetpts=PTS-STARTPTS[a{segment_index}];")
            segment_index += 1
            
            # Concatenate all segments
            concat_inputs = ''.join([f"[a{i}]" for i in range(segment_index)])
            filter_parts.append(f"{concat_inputs}concat=n={segment_index}:v=0:a=1[out]")
            
            filter_complex = ''.join(filter_parts)
            
            (
                ffmpeg
                .input(input_path)
                .output(output_path, **{'filter_complex': filter_complex, 'map': '[out]'})
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info("Audio cuts applied", input=input_path, output=output_path, cuts=len(cut_list))
            return output_path
            
        except Exception as e:
            raise AgentError(f"Failed to apply audio cuts: {e}")
    
    def _generate_clean_transcript(self, original_transcript: List[Dict], cut_list: List[Tuple[float, float]]) -> str:
        """Generate clean transcript text with filler words removed."""
        clean_words = []
        cut_ranges = set()
        
        # Mark all time ranges that should be cut
        for start_time, end_time in cut_list:
            cut_ranges.add((start_time, end_time))
        
        for word_info in original_transcript:
            word_start = word_info['start_time']
            word_end = word_info['end_time']
            
            # Check if this word falls within any cut range
            should_cut = False
            for cut_start, cut_end in cut_ranges:
                if (word_start >= cut_start and word_end <= cut_end) or word_info['word'].strip() in self.FILLER_WORDS:
                    should_cut = True
                    break
            
            if not should_cut:
                clean_words.append(word_info['word'])
        
        return ' '.join(clean_words) 