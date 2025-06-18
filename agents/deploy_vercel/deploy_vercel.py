"""Deploy Vercel Agent - Trigger static-site redeploy."""

import os
import subprocess
from typing import Dict
import structlog
from google.adk.agents import BaseAgent

logger = structlog.get_logger()


class AgentError(Exception):
    """Custom exception for recoverable agent errors."""
    pass


class Agent(BaseAgent):
    """Deploy Vercel Agent - see SPEC.md for full contract."""
    
    name = "deploy_vercel"
    description = "Trigger Vercel deployment for hub.momit.fm"
    version = "0.1.0"
    
    def __init__(self, repo_path: str = "hub.momit.fm"):
        super().__init__()
        self.repo_path = repo_path
        
    async def run(self, state: Dict) -> Dict:
        """Trigger Vercel production deployment.
        
        Args:
            state (dict): Input/Output shared pipeline state.
            
        Returns:
            dict: Updated slice with deployment information.
        """
        logger.info("Starting Vercel deployment")
        
        episode_package_dir = state.get("episode_package_dir")
        if not episode_package_dir:
            raise AgentError("No episode package directory found in state")
            
        # Check for Vercel token
        vercel_token = os.getenv("VERCEL_TOKEN")
        if not vercel_token:
            raise AgentError("VERCEL_TOKEN environment variable not set")
            
        try:
            # Set environment variable for Vercel CLI
            env = os.environ.copy()
            env["VERCEL_TOKEN"] = vercel_token
            
            # Change to repository directory
            original_cwd = os.getcwd()
            if os.path.exists(self.repo_path):
                os.chdir(self.repo_path)
                logger.info("Changed to repository directory", path=self.repo_path)
            
            # Run vercel deploy --prod
            result = subprocess.run(
                ["vercel", "deploy", "--prod", "--yes"],
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Restore original directory
            os.chdir(original_cwd)
            
            if result.returncode == 0:
                deployment_url = result.stdout.strip().split('\n')[-1]
                logger.info("Vercel deployment completed successfully",
                           deployment_url=deployment_url)
                
                return {
                    "vercel_deployment_url": deployment_url,
                    "vercel_deployment_status": "success"
                }
            else:
                error_message = result.stderr or result.stdout
                logger.error("Vercel deployment failed", 
                           error=error_message,
                           return_code=result.returncode)
                raise AgentError(f"Vercel deployment failed: {error_message}")
                
        except subprocess.TimeoutExpired:
            raise AgentError("Vercel deployment timed out after 5 minutes")
        except FileNotFoundError:
            raise AgentError("Vercel CLI not found. Please install Vercel CLI first.")
        except Exception as e:
            raise AgentError(f"Failed to deploy to Vercel: {e}")
        finally:
            # Ensure we restore original directory
            try:
                os.chdir(original_cwd)
            except:
                pass 