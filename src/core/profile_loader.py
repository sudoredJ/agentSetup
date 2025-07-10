import yaml
import os
import logging
from typing import Dict, Any
from src.core.config_loader import load_config as load_system_config

def _legacy_load_system_config(path: str = "configs/system_config.yaml") -> Dict[str, Any]:
    """Loads the main system configuration."""
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Substitute environment variables
        for section, settings in config.items():
            for key, value in settings.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    var_name = value[2:-1]
                    config[section][key] = os.environ.get(var_name)
        return config
    except FileNotFoundError:
        logging.error(f"System config file not found at {path}")
        return {}
    except Exception as e:
        logging.error(f"Error loading system config: {e}")
        return {}

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