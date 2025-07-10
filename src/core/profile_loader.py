import yaml
import os
import logging
from typing import Dict, Any

def load_agent_profile(agent_name: str, path: str = "configs/agents") -> Dict[str, Any]:
    """Loads a specific agent's profile."""
    profile_path = os.path.join(path, f"{agent_name.lower()}_agent.yaml")
    try:
        with open(profile_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Agent profile not found for {agent_name} at {profile_path}")
        return {}
    except Exception as e:
        logging.error(f"Error loading agent profile for {agent_name}: {e}")
        return {} 