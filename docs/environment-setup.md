# Environment Configuration Guide

This document explains how to configure the invoice extraction system for different computers with different file paths.

## Quick Start

1. **Copy the example file**:
   ```bash
   cp environments.json.example environments.json
   ```

2. **Edit `environments.json`** with your computer's path:
   ```json
   {
     "environments": {
       "my_computer": {
         "description": "My Computer Name",
         "source_dir": "/your/path/to/Bills",
         "output_dir": "output",
         "max_workers": 4
       }
     },
     "default": "my_computer"
   }
   ```

3. **Verify it works**:
   ```bash
   uv run python scripts/check_environment.py
   ```

## Configuration File Structure

The `environments.json` file has this structure:

```json
{
  "environments": {
    "env_name": {
      "description": "Human-readable description",
      "source_dir": "/absolute/path/to/invoice/Bills/directory",
      "output_dir": "output",
      "max_workers": 4
    }
  },
  "default": "env_name"
}
```

### Field Descriptions

- **`environments`**: Container for all environment configurations
- **`env_name`**: Unique identifier (use lowercase, underscores)
- **`description`**: Human-readable name shown in listings
- **`source_dir`**: Absolute path to the `Bills/` directory containing vendor folders
- **`output_dir`**: Where to write CSV exports (relative or absolute)
- **`max_workers`**: Number of parallel workers for batch processing
- **`default`**: Which environment to use when not specified

## Multiple Computers

If you use multiple computers, add all of them to `environments.json`:

```json
{
  "environments": {
    "work_mac": {
      "description": "Work MacBook Pro",
      "source_dir": "/Users/dalton/Library/CloudStorage/Dropbox/.../Bills",
      "output_dir": "output",
      "max_workers": 4
    },
    "home_desktop": {
      "description": "Home Linux Desktop",
      "source_dir": "/home/dalton/Dropbox/.../Bills",
      "output_dir": "output",
      "max_workers": 8
    },
    "laptop": {
      "description": "Travel Laptop",
      "source_dir": "/home/user/Dropbox/.../Bills",
      "output_dir": "output",
      "max_workers": 2
    }
  },
  "default": "work_mac"
}
```

## Usage Methods

### Method 1: Use Default Environment

Set which environment is default in `environments.json`:

```json
"default": "home_desktop"
```

Then run scripts normally:

```bash
uv run python tests/test_reflex_batch.py
```

### Method 2: Environment Variable

Override the default with `INVOICE_ENV`:

```bash
export INVOICE_ENV=laptop
uv run python tests/test_reflex_batch.py
```

Or for a single run:

```bash
INVOICE_ENV=work_mac uv run python tests/test_reflex_batch.py
```

### Method 3: Explicit in Code

Load a specific environment in your Python script:

```python
from config import Config

# Load specific environment
Config.load_environment("home_desktop")

# Now use Config.SOURCE_DIR
reflex_dir = Config.SOURCE_DIR / "Reflex"
```

### Method 4: Complete Override

Override individual settings with environment variables:

```bash
export INVOICE_SOURCE_DIR="/custom/path/to/Bills"
export MAX_WORKERS=16
uv run python tests/test_reflex_batch.py
```

## Priority Order

Configuration is resolved in this order (highest to lowest priority):

1. **Environment variables** (`INVOICE_SOURCE_DIR`, `OUTPUT_DIR`, `MAX_WORKERS`, etc.)
2. **Explicit load call** (`Config.load_environment("name")`)
3. **`INVOICE_ENV` variable** (selects which environment from config file)
4. **Default from config** (the `"default"` field in `environments.json`)
5. **Hardcoded defaults** (fallback values in `config.py`)

## Checking Your Configuration

### List All Environments

```bash
uv run python scripts/check_environment.py --list
```

Output:
```
Available Environments:
============================================================

work_mac (default)
  Description: Work MacBook Pro
  Source Dir:  /Users/dalton/Library/CloudStorage/Dropbox/.../Bills

home_desktop
  Description: Home Linux Desktop
  Source Dir:  /home/dalton/Dropbox/.../Bills
```

### Check Current/Default Environment

```bash
uv run python scripts/check_environment.py
```

Output:
```
Loaded Environment: work_mac
============================================================
Source Directory: /Users/dalton/Library/CloudStorage/Dropbox/.../Bills
Output Directory: output
Max Workers:      4

Source exists:    True
```

### Check Specific Environment

```bash
uv run python scripts/check_environment.py home_desktop
```

## Troubleshooting

### "Environment configuration file not found"

**Cause**: `environments.json` doesn't exist.

**Solution**:
```bash
cp environments.json.example environments.json
# Edit with your paths
```

### "Environment 'xyz' not found"

**Cause**: You specified an environment that doesn't exist in `environments.json`.

**Solution**: Run `--list` to see available environments:
```bash
uv run python scripts/check_environment.py --list
```

### "Source directory does not exist"

**Cause**: The `source_dir` path in your environment doesn't exist on this computer.

**Solutions**:
1. Verify the path is correct in `environments.json`
2. Ensure Dropbox/cloud storage is synced and mounted
3. Check spelling and case sensitivity (especially on Linux)

### Wrong Environment Loading

**Cause**: You might have `INVOICE_ENV` set in your shell.

**Check**:
```bash
echo $INVOICE_ENV
```

**Clear**:
```bash
unset INVOICE_ENV
```

## Best Practices

1. **Add to `.gitignore`**: The `environments.json` file should NOT be committed to git (it already is ignored). Each developer maintains their own copy.

2. **Update the example**: If you add new configuration options, update `environments.json.example` for other users.

3. **Use descriptive names**: Use environment names like `work_mac`, `home_linux`, `laptop` rather than generic names.

4. **Verify before batch runs**: Always run `check_environment.py` before processing large batches to ensure you're using the correct source location.

5. **Document your paths**: Add good descriptions to help identify which computer each environment represents.

## Git and environments.json

The `environments.json` file is **ignored by git** (listed in `.gitignore`). This is intentional because:

- File paths are different on each computer
- Each developer needs their own configuration
- Prevents accidentally committing personal paths

The `environments.json.example` file **is tracked** and provides a template for new users.

## Platform-Specific Notes

### macOS

- Dropbox path: `/Users/username/Library/CloudStorage/Dropbox/...`
- Or traditional: `/Users/username/Dropbox/...`
- Use forward slashes in paths
- Paths are case-insensitive but preserve case

### Linux

- Dropbox path: `/home/username/Dropbox/...`
- Use forward slashes in paths
- Paths are case-sensitive
- Check that Dropbox daemon is running

### Windows (if needed)

- Dropbox path: `C:/Users/username/Dropbox/...`
- Use forward slashes (recommended) or double backslashes
- Drive letter is case-insensitive
- Example: `C:/Users/dalton/Dropbox/.../Bills`
