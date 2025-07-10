import os, sys, re, yaml, logging

# ---------------------------------------------------------------------------
# Shared config loader
# ---------------------------------------------------------------------------

def load_config(path: str = 'configs/system_config.yaml') -> dict:
    """Load YAML configuration with ${ENV_VAR} substitution.

    The function reads the given YAML file as a raw string so that placeholders
    like ${MY_ENV_VAR} (optionally wrapped in quotes) are substituted with the
    corresponding environment variable before the YAML is parsed.
    If a referenced environment variable is missing, the process exits with an
    error so mis-configuration is caught early.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find placeholders of the form ${VAR}
        placeholders = re.findall(r'\$\{(\w+)\}', content)
        for ph in placeholders:
            env_val = os.environ.get(ph)
            if env_val is None:
                logging.error(f"Missing env var referenced in config: {ph}")
                sys.exit(1)
            # Replace both quoted and un-quoted occurrences
            content = content.replace(f'"${{{ph}}}"', f'"{env_val}"')
            content = content.replace(f'${{{ph}}}', env_val)

        return yaml.safe_load(content)
    except Exception as exc:
        logging.error(f"Config error: {exc}")
        sys.exit(1) 