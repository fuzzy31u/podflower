"""X Post Agent - Post announcement tweet."""

import os
from typing import Dict
import structlog
import tweepy
from google.adk.agents import BaseAgent

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """X Post Agent - see SPEC.md for full contract."""
    
    name = "post_to_x"
    description = "Post episode announcement to X (Twitter)"
    version = "0.1.0"
    
    def __init__(self):
        super().__init__()
        # X API credentials
        self.consumer_key = os.getenv("X_CONSUMER_KEY")
        self.consumer_secret = os.getenv("X_CONSUMER_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        
    async def run(self, state: Dict) -> Dict:
        """Post episode announcement to X.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with X post information.
        """
        logger.info("Starting X post agent")
        
        # Get required data
        metadata = state.get("metadata", {})
        wordpress_post_url = state.get("wordpress_post_url")
        episode_package_dir = state.get("episode_package_dir")
        
        if not metadata:
            raise AgentError("No metadata found in state")
            
        # Validate X credentials
        if not all([self.consumer_key, self.consumer_secret, 
                   self.access_token, self.access_token_secret]):
            raise AgentError("X API credentials not configured")
            
        try:
            # Initialize X API client
            client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Create post content
            post_text = self._create_post_text(metadata, wordpress_post_url)
            
            # Post to X
            response = client.create_tweet(text=post_text)
            
            tweet_id = response.data['id']
            tweet_url = f"https://x.com/momitfm/status/{tweet_id}"
            
            logger.info("X post created successfully",
                       tweet_id=tweet_id,
                       tweet_url=tweet_url,
                       text=post_text)
            
            return {
                "x_tweet_id": tweet_id,
                "x_tweet_url": tweet_url,
                "x_post_text": post_text
            }
            
        except Exception as e:
            raise AgentError(f"Failed to post to X: {e}")
    
    def _create_post_text(self, metadata: Dict, episode_url: str = None) -> str:
        """Create X post text according to SPEC format."""
        title = metadata.get("title", "新しいエピソード")
        
        # Base post text from SPEC
        post_text = f"新しいエピソード公開🎙️\n{title} #momitfm"
        
        # Add episode URL if available
        if episode_url:
            post_text += f"\n{episode_url}"
        else:
            # Fallback to main website
            post_text += f"\nhttps://momit.fm"
        
        # Ensure post is within X character limit (280 characters)
        if len(post_text) > 280:
            # Truncate title if necessary
            max_title_length = 280 - len("新しいエピソード公開🎙️\n #momitfm\nhttps://momit.fm")
            if max_title_length > 10:
                truncated_title = title[:max_title_length-3] + "..."
                post_text = f"新しいエピソード公開🎙️\n{truncated_title} #momitfm"
                if episode_url:
                    post_text += f"\n{episode_url}"
                else:
                    post_text += f"\nhttps://momit.fm"
        
        return post_text 