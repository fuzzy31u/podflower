"""WordPress Publisher Agent - Publish article to WordPress."""

import os
import requests
from typing import Dict, Optional, ClassVar
import structlog
from google.adk.agents import BaseAgent

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """WordPress Publisher Agent - see SPEC.md for full contract."""
    name: str = "wordpress_publish"
    description: str = "Publish show notes to WordPress with featured image from Unsplash"
    version: str = "0.1.0"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'wp_base_url', os.getenv("WORDPRESS_BASE_URL", "https://momithub.com"))
        object.__setattr__(self, 'wp_username', os.getenv("WORDPRESS_USERNAME"))
        object.__setattr__(self, 'wp_password', os.getenv("WORDPRESS_APP_PASSWORD"))
        object.__setattr__(self, 'unsplash_access_key', os.getenv("UNSPLASH_ACCESS_KEY"))
        
    async def run(self, state: Dict) -> Dict:
        """Publish episode to WordPress.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with WordPress post information.
        """
        logger.info("Starting WordPress publishing")
        
        # Get required data
        metadata = state.get("metadata", {})
        shownote_md = state.get("shownote_md", "")
        episode_package_dir = state.get("episode_package_dir")
        
        if not metadata:
            raise AgentError("No metadata found in state")
        if not shownote_md:
            raise AgentError("No show notes found in state")
            
        # Validate WordPress credentials
        if not all([self.wp_username, self.wp_password]):
            raise AgentError("WordPress credentials not configured")
            
        try:
            # 1. Get featured image from Unsplash
            featured_image_url = await self._get_featured_image(metadata.get("title", "podcast"))
            
            # 2. Convert markdown to HTML
            post_content = self._markdown_to_html(shownote_md)
            
            # 3. Create WordPress post
            post_data = {
                "title": metadata.get("title", "New Episode"),
                "content": post_content,
                "status": "publish",
                "categories": [1],  # Assuming category ID 1 for podcast
                "tags": ["podcast", "momit.fm"],
                "meta": {
                    "episode_duration": metadata.get("duration_seconds", 0),
                    "episode_date": metadata.get("created_at"),
                    "audio_file_size": metadata.get("file_size_bytes", 0)
                }
            }
            
            # Add featured image if available
            if featured_image_url:
                post_data["featured_media"] = await self._upload_featured_image(featured_image_url)
            
            # 4. Publish post
            post_response = await self._create_wordpress_post(post_data)
            
            logger.info("WordPress post published successfully",
                       post_id=post_response.get("id"),
                       post_url=post_response.get("link"),
                       title=metadata.get("title"))
            
            return {
                "wordpress_post_id": post_response.get("id"),
                "wordpress_post_url": post_response.get("link"),
                "wordpress_featured_image": featured_image_url
            }
            
        except Exception as e:
            raise AgentError(f"Failed to publish to WordPress: {e}")
    
    async def _get_featured_image(self, title: str) -> Optional[str]:
        """Get featured image from Unsplash API."""
        if not self.unsplash_access_key:
            logger.warning("Unsplash access key not configured, skipping featured image")
            return None
            
        try:
            # Search for image based on title keywords
            search_query = "podcast microphone technology"  # Default search
            if "AI" in title or "人工知能" in title:
                search_query = "artificial intelligence technology"
            elif "プログラミング" in title or "コード" in title:
                search_query = "programming code computer"
            
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {self.unsplash_access_key}"}
            params = {
                "query": search_query,
                "per_page": 1,
                "orientation": "landscape"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data["results"]:
                image_url = data["results"][0]["urls"]["regular"]
                logger.info("Featured image found", url=image_url, query=search_query)
                return image_url
                
        except Exception as e:
            logger.warning("Failed to get featured image from Unsplash", error=str(e))
        
        return None
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML (basic conversion)."""
        # Basic markdown to HTML conversion
        html_content = markdown_content
        
        # Headers
        html_content = html_content.replace("# ", "<h1>").replace("\n# ", "</h1>\n<h1>")
        html_content = html_content.replace("## ", "<h2>").replace("\n## ", "</h2>\n<h2>")
        html_content = html_content.replace("### ", "<h3>").replace("\n### ", "</h3>\n<h3>")
        
        # Lists
        lines = html_content.split('\n')
        in_list = False
        processed_lines = []
        
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                processed_lines.append(f'  <li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                processed_lines.append(line)
        
        if in_list:
            processed_lines.append('</ul>')
        
        html_content = '\n'.join(processed_lines)
        
        # Paragraphs
        html_content = html_content.replace('\n\n', '</p>\n<p>')
        html_content = f'<p>{html_content}</p>'
        
        return html_content
    
    async def _upload_featured_image(self, image_url: str) -> Optional[int]:
        """Upload featured image to WordPress media library."""
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Upload to WordPress
            files = {"file": ("featured-image.jpg", response.content, "image/jpeg")}
            
            wp_media_url = f"{self.wp_base_url}/wp-json/wp/v2/media"
            auth = (self.wp_username, self.wp_password)
            
            upload_response = requests.post(wp_media_url, files=files, auth=auth, timeout=30)
            upload_response.raise_for_status()
            
            media_data = upload_response.json()
            return media_data.get("id")
            
        except Exception as e:
            logger.warning("Failed to upload featured image", error=str(e))
            return None
    
    async def _create_wordpress_post(self, post_data: Dict) -> Dict:
        """Create WordPress post using REST API."""
        wp_posts_url = f"{self.wp_base_url}/wp-json/wp/v2/posts"
        auth = (self.wp_username, self.wp_password)
        
        response = requests.post(
            wp_posts_url,
            json=post_data,
            auth=auth,
            timeout=30
        )
        response.raise_for_status()
        
        return response.json() 