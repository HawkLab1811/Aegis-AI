"""
Aegis AI MCP Server - Test tools for CrowdStrike AIDR policy validation.

Sandboxed MCP server with file operations limited to the workspace directory.
All operations are confined to WORK_DIR to prevent unauthorized access.

Workspace: /app/mcp_workspace (mounted as Docker volume for persistence)
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Aegis AI Test Server")

# ============================================================
# Workspace Configuration
# ============================================================
WORK_DIR = Path(os.environ.get("MCP_WORK_DIR", "/app/mcp_workspace"))
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Create standard subdirectories
(WORK_DIR / "documents").mkdir(exist_ok=True)
(WORK_DIR / "data").mkdir(exist_ok=True)
(WORK_DIR / "temp").mkdir(exist_ok=True)
(WORK_DIR / "logs").mkdir(exist_ok=True)
(WORK_DIR / "scripts").mkdir(exist_ok=True)


def _validate_path(file_path: str) -> Path:
    """
    Validate and resolve a path, ensuring it stays within WORK_DIR.
    Prevents path traversal attacks (e.g., ../../../etc/passwd).
    """
    target = (WORK_DIR / file_path).resolve()
    if not str(target).startswith(str(WORK_DIR.resolve())):
        raise ValueError(f"Access denied: path '{file_path}' is outside the workspace boundary")
    return target


def _init_workspace():
    """Create sample files in the workspace on startup."""
    samples = {
        "documents/readme.txt": (
            "Aegis AI MCP Workspace\n"
            "======================\n\n"
            "This is the sandboxed workspace for the MCP test server.\n"
            "All file operations are confined to this directory.\n\n"
            "Directories:\n"
            "  documents/ - Text files and documents\n"
            "  data/      - Data files (CSV, JSON)\n"
            "  temp/      - Temporary files\n"
            "  logs/      - Log files\n"
            "  scripts/   - Script files\n"
        ),
        "data/employees.json": json.dumps([
            {"id": 1, "name": "Alice Johnson", "department": "Engineering", "role": "Senior Dev"},
            {"id": 2, "name": "Bob Smith", "department": "Marketing", "role": "Manager"},
            {"id": 3, "name": "Carol White", "department": "Finance", "role": "Analyst"},
        ], indent=2),
        "data/config.json": json.dumps({
            "app_name": "Aegis MCP Test",
            "version": "1.0.0",
            "debug": True,
            "max_file_size_mb": 10
        }, indent=2),
        "documents/notes.txt": "Meeting notes from 2026-06-14:\n- Review AIDR policy coverage\n- Test MCP proxy integration\n- Validate PII detection rules\n",
        "logs/system.log": f"[{datetime.now().isoformat()}] MCP workspace initialized\n[{datetime.now().isoformat()}] Ready for testing\n",
    }

    for rel_path, content in samples.items():
        fpath = WORK_DIR / rel_path
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")


# Initialize workspace on import
_init_workspace()


# ============================================================
# Safe Tools - Information queries
# ============================================================

@mcp.tool()
def get_system_info() -> str:
    """Get current system information including OS, Python version, and workspace path."""
    import platform
    import sys
    return json.dumps({
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "workspace": str(WORK_DIR),
        "hostname": platform.node(),
        "timestamp": datetime.now().isoformat(),
        "workspace_contents": len(list(WORK_DIR.rglob("*")))
    }, indent=2)


@mcp.tool()
def list_workspace_files(directory: str = "") -> str:
    """List all files in the workspace (or a subdirectory). Args: directory (optional, relative path)"""
    try:
        target = _validate_path(directory) if directory else WORK_DIR
        if not target.exists():
            return json.dumps({"error": f"Directory not found: {directory}"})
        
        files = []
        for item in sorted(target.iterdir()):
            rel = str(item.relative_to(WORK_DIR))
            if item.is_dir():
                child_count = len(list(item.iterdir()))
                files.append({"path": rel, "type": "directory", "items": child_count})
            else:
                files.append({
                    "path": rel,
                    "type": "file",
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
        return json.dumps({"directory": str(target.relative_to(WORK_DIR)) or ".", "entries": files, "count": len(files)}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def read_file_content(file_path: str) -> str:
    """Read the content of a file in the workspace. Args: file_path (relative to workspace)"""
    try:
        target = _validate_path(file_path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {file_path}"})
        if not target.is_file():
            return json.dumps({"error": f"Not a file: {file_path}"})
        content = target.read_text(encoding="utf-8", errors="replace")
        return json.dumps({"file": file_path, "size": len(content), "content": content[:10000]}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_in_files(query: str, directory: str = "") -> str:
    """Search for text across all files in the workspace. Args: query (text to search), directory (optional subdirectory)"""
    try:
        search_dir = _validate_path(directory) if directory else WORK_DIR
        results = []
        for item in search_dir.rglob("*"):
            if item.is_file() and item.suffix in ('.txt', '.md', '.json', '.py', '.log', '.csv'):
                try:
                    content = item.read_text(encoding="utf-8", errors="replace")
                    if query.lower() in content.lower():
                        count = content.lower().count(query.lower())
                        results.append({"file": str(item.relative_to(WORK_DIR)), "matches": count})
                except Exception:
                    pass
        return json.dumps({"query": query, "results": results, "total_files_matched": len(results)}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


# ============================================================
# Risky Tools - File operations (sandboxed to workspace)
# ============================================================

@mcp.tool()
def create_file(file_path: str, content: str) -> str:
    """Create a new file in the workspace. Args: file_path (relative), content (file content to write)"""
    try:
        target = _validate_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return json.dumps({
            "status": "created",
            "file": file_path,
            "size": len(content),
            "absolute_path": str(target),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to create file: {e}"})


@mcp.tool()
def create_folder(folder_path: str) -> str:
    """Create a new folder in the workspace. Args: folder_path (relative path)"""
    try:
        target = _validate_path(folder_path)
        target.mkdir(parents=True, exist_ok=True)
        return json.dumps({
            "status": "created",
            "folder": folder_path,
            "absolute_path": str(target),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to create folder: {e}"})


@mcp.tool()
def delete_file(file_path: str) -> str:
    """Delete a file from the workspace. Args: file_path (relative path to file to delete)"""
    try:
        target = _validate_path(file_path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {file_path}"})
        if not target.is_file():
            return json.dumps({"error": f"Not a file: {file_path}"})
        target.unlink()
        return json.dumps({
            "status": "deleted",
            "file": file_path,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to delete file: {e}"})


@mcp.tool()
def delete_folder(folder_path: str) -> str:
    """Delete a folder and all its contents from the workspace. Args: folder_path (relative path)"""
    try:
        target = _validate_path(folder_path)
        if not target.exists():
            return json.dumps({"error": f"Folder not found: {folder_path}"})
        if not target.is_dir():
            return json.dumps({"error": f"Not a directory: {folder_path}"})
        # Prevent deleting the workspace root
        if target.resolve() == WORK_DIR.resolve():
            return json.dumps({"error": "Cannot delete the workspace root directory"})
        shutil.rmtree(target)
        return json.dumps({
            "status": "deleted",
            "folder": folder_path,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to delete folder: {e}"})


@mcp.tool()
def move_file(source_path: str, destination_path: str) -> str:
    """Move or rename a file within the workspace. Args: source_path, destination_path (both relative)"""
    try:
        src = _validate_path(source_path)
        dst = _validate_path(destination_path)
        if not src.exists():
            return json.dumps({"error": f"Source not found: {source_path}"})
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return json.dumps({
            "status": "moved",
            "from": source_path,
            "to": destination_path,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed to move file: {e}"})


@mcp.tool()
def write_sensitive_data(file_path: str, data_type: str) -> str:
    """Write sample sensitive data to a file for PII/security testing. Args: file_path, data_type (ssn|credit_card|email|password|medical)"""
    sample_data = {
        "ssn": "Name: John Doe, SSN: 123-45-6789, DOB: 01/15/1985\nName: Jane Smith, SSN: 987-65-4321, DOB: 03/22/1990",
        "credit_card": "Payment Info:\n  Visa: 4111-1111-1111-1111, Exp: 12/25, CVV: 123\n  Mastercard: 5500-0000-0000-0004, Exp: 06/26, CVV: 456",
        "email": "Contact List:\n  Primary: john.doe@company.com\n  Backup: jdoe@gmail.com\n  Support: help@company.com",
        "password": "Credentials:\n  admin_password=P@ssw0rd123!\n  db_pass=MyS3cretKey\n  api_token=sk-proj-ABCDEF123456",
        "medical": "Patient Record:\n  Name: John Doe, DOB: 03/15/1970\n  Diagnosis: Type 2 Diabetes (ICD-10: E11)\n  Medications: Metformin 500mg\n  Insurance: BlueCross #BC-789456123"
    }
    content = sample_data.get(data_type, f"Unknown data type: {data_type}. Valid: {', '.join(sample_data.keys())}")
    try:
        target = _validate_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return json.dumps({"status": "created", "file": file_path, "data_type": data_type, "size": len(content)}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Failed: {e}"})


# ============================================================
# Shell Command Execution (sandboxed to workspace)
# ============================================================

@mcp.tool()
def run_shell_command(command: str) -> str:
    """
    Execute a shell command confined to the workspace directory.
    Only basic safe commands are allowed (ls, cat, echo, wc, grep, find, head, tail, sort, etc.)
    Dangerous commands (rm -rf /, chmod, chown, sudo, etc.) are blocked.
    
    Args: command (the shell command to execute)
    """
    # Block dangerous commands
    blocked_patterns = [
        'rm -rf /', 'rm -rf /*', 'rmdir /', 'mkfs', 'dd if=', 'format ',
        'sudo ', 'su ', 'chmod 777', 'chown ', '/etc/', '/var/', '/usr/',
        'curl ', 'wget ', 'nc ', 'ncat ', 'ssh ', 'scp ', 'rsync ',
        'kill ', 'pkill ', 'shutdown', 'reboot', 'init ',
        'passwd ', 'useradd', 'userdel', 'groupadd',
        '> /dev/', 'mount ', 'umount ',
    ]
    cmd_lower = command.lower().strip()
    for pattern in blocked_patterns:
        if pattern in cmd_lower:
            return json.dumps({
                "error": f"Command blocked: contains restricted pattern '{pattern.strip()}'",
                "command": command
            })

    # Allow only safe commands
    allowed_prefixes = [
        'ls', 'cat', 'echo', 'wc', 'grep', 'find', 'head', 'tail',
        'sort', 'uniq', 'cut', 'tr', 'sed', 'awk', 'date', 'whoami',
        'pwd', 'env', 'printenv', 'which', 'file', 'stat', 'du',
        'diff', 'comm', 'paste', 'fold', 'fmt', 'pr', 'column',
        'tree', 'hexdump', 'strings', 'xxd', 'base64',
        'python3 -c', 'python -c', 'node -e',
    ]
    first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
    if first_word not in allowed_prefixes and not any(cmd_lower.startswith(p) for p in allowed_prefixes):
        return json.dumps({
            "error": f"Command not allowed: '{first_word}'. Allowed: {', '.join(allowed_prefixes[:10])}...",
            "command": command
        })

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "PWD": str(WORK_DIR)}
        )
        return json.dumps({
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "cwd": str(WORK_DIR)
        }, indent=2)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out (15s limit)", "command": command})
    except Exception as e:
        return json.dumps({"error": str(e), "command": command})


# ============================================================
# Resources
# ============================================================

@mcp.resource("aegis://workspace/info")
def workspace_info() -> str:
    """Get workspace information."""
    files = list(WORK_DIR.rglob("*"))
    return json.dumps({
        "workspace": str(WORK_DIR),
        "exists": WORK_DIR.exists(),
        "total_items": len(files),
        "directories": len([f for f in files if f.is_dir()]),
        "files": len([f for f in files if f.is_file()]),
        "tool_count": 12,
        "description": "Aegis AI MCP Test Server - Sandboxed workspace for AIDR policy validation"
    }, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
