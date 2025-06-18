"""Title & Show-note Generator Agent - Generate JP titles & show notes."""

import json
from typing import Dict, List
import structlog
from google.adk.agents import LlmAgent

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(LlmAgent):
    """Title Notes Agent - see SPEC.md for full contract."""
    
    name = "title_notes"
    description = "Generate Japanese titles and markdown show notes using LLM"
    version = "0.1.0"
    
    def __init__(self):
        super().__init__(
            model="gemini-2.0-flash",
            instruction="""あなたは日本のポッドキャスト「momit.fm」の編集者です。
            音声の転写を基に、魅力的なエピソードタイトルと詳細な番組ノートを作成してください。

            要件:
            1. エピソードタイトルを5つ提案してください（各30文字以内）
            2. 番組ノートをMarkdown形式で作成してください
            3. 番組ノートは以下の構成で作成してください：
               - # 概要
               - # 主なトピック
               - # タイムスタンプ付きハイライト
               - # 関連リンク

            必ず以下のJSON形式で回答してください：
            {
                "title_candidates": ["タイトル1", "タイトル2", "タイトル3", "タイトル4", "タイトル5"],
                "shownote_md": "# 概要\\n..."
            }"""
        )
    
    async def run(self, state: Dict) -> Dict:
        """Generate Japanese titles and show notes from transcript.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with title candidates and show notes.
        """
        logger.info("Starting title and show notes generation")
        
        transcript = state.get("transcript")
        if not transcript:
            raise AgentError("No transcript found in state")
            
        # Prepare prompt with transcript
        user_prompt = f"""以下の音声転写からポッドキャストの番組情報を生成してください：

転写テキスト:
{transcript[:4000]}  # Limit to first 4000 chars to avoid token limits

上記の転写を基に、5つのタイトル候補と詳細な番組ノートを生成してください。"""
        
        try:
            # Generate content using LLM
            response = await self.generate_content(user_prompt)
            
            # Extract JSON from response
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Validate response structure
            if not self._validate_response(result):
                raise AgentError("Generated response does not match required schema")
            
            logger.info("Title and show notes generated successfully",
                       title_count=len(result["title_candidates"]))
            
            return {
                "title_candidates": result["title_candidates"],
                "shownote_md": result["shownote_md"]
            }
            
        except json.JSONDecodeError as e:
            raise AgentError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise AgentError(f"Failed to generate titles and show notes: {e}")
    
    def _validate_response(self, result: Dict) -> bool:
        """Validate that the response matches the required schema."""
        try:
            # Check required keys
            if "title_candidates" not in result or "shownote_md" not in result:
                return False
                
            # Check title_candidates is list of 5 strings
            title_candidates = result["title_candidates"]
            if not isinstance(title_candidates, list) or len(title_candidates) != 5:
                return False
                
            for title in title_candidates:
                if not isinstance(title, str) or len(title) == 0:
                    return False
                    
            # Check shownote_md is non-empty string
            shownote = result["shownote_md"]
            if not isinstance(shownote, str) or len(shownote) == 0:
                return False
                
            # Check that shownote contains required sections
            required_sections = ["# 概要", "# 主なトピック"]
            for section in required_sections:
                if section not in shownote:
                    return False
                    
            return True
            
        except Exception:
            return False
    
    async def generate_content(self, prompt: str) -> str:
        """Generate content using the configured LLM."""
        # This would be implemented using the actual ADK LlmAgent functionality
        # For now, providing a mock implementation
        
        # In a real implementation, this would use:
        # result = await super().run({"message": prompt})
        # return result["response"]
        
        # Mock response for development
        return """{
            "title_candidates": [
                "今週のテック話題をディープダイブ",
                "AI時代のプログラマーの未来",
                "スタートアップの現実と理想",
                "エンジニアのキャリア戦略",
                "テクノロジーが変える働き方"
            ],
            "shownote_md": "# 概要\\n今回のエピソードでは、最新のテクノロジートレンドについて議論します。\\n\\n# 主なトピック\\n- AI技術の最新動向\\n- プログラミング言語の進化\\n- リモートワークの影響\\n\\n# タイムスタンプ付きハイライト\\n- 00:05:30 - AI開発ツールの紹介\\n- 00:12:15 - 新しいフレームワークの解説\\n- 00:18:45 - 業界の将来予測\\n\\n# 関連リンク\\n- [momit.fm公式サイト](https://momit.fm)\\n- [GitHub Repository](https://github.com/momitfm)"
        }""" 