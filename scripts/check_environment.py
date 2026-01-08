#!/usr/bin/env python3
"""Check and manage environment configuration for invoice extraction."""

import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


def list_environments():
    """List all available environments."""
    try:
        envs = Config.list_environments()

        if not envs:
            print("No environments.json file found.")
            print("\nCreate environments.json with your computer-specific settings:")
            print('{\n  "environments": {\n    "computer_name": {')
            print('      "description": "Description",')
            print('      "source_dir": "/path/to/invoices",')
            print('      "output_dir": "output",')
            print('      "max_workers": 4')
            print('    }\n  },\n  "default": "computer_name"\n}')
            return

        print("Available Environments:")
        print("=" * 60)

        for env_name, settings in envs.items():
            default_marker = " (default)" if settings["is_default"] else ""
            print(f"\n{env_name}{default_marker}")
            print(f"  Description: {settings['description']}")
            print(f"  Source Dir:  {settings['source_dir']}")

    except Exception as e:
        print(f"Error listing environments: {e}")


def check_environment(env_name: str = None):
    """Check if environment is valid and show its configuration."""
    try:
        loaded_env = Config.load_environment(env_name)

        print(f"\nLoaded Environment: {loaded_env}")
        print("=" * 60)
        print(f"Source Directory: {Config.SOURCE_DIR}")
        print(f"Output Directory: {Config.OUTPUT_DIR}")
        print(f"Max Workers:      {Config.MAX_WORKERS}")
        print(f"\nSource exists:    {Config.SOURCE_DIR.exists()}")

        if not Config.SOURCE_DIR.exists():
            print("\nWARNING: Source directory does not exist!")
            print("Please check your environments.json configuration.")

        return True

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return False
    except ValueError as e:
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check and manage environment configuration"
    )
    parser.add_argument(
        "environment",
        nargs="?",
        help="Environment name to check (if not provided, uses default)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available environments",
    )

    args = parser.parse_args()

    if args.list:
        list_environments()
    elif args.environment:
        check_environment(args.environment)
    else:
        check_environment()


if __name__ == "__main__":
    main()
