"""MCP Server management service."""

import sys
from typing import Optional, List
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.mcp_server import MCPServer
from app.utils.encryption import encrypt_value, decrypt_value
import json

MCP_SERVER_DIR = Path(__file__).parent.parent.parent / "mcp_server"
PYTHON_CMD = sys.executable


# Default MCP tool descriptions for LLM context
MCP_TOOL_DESCRIPTIONS = {
    "get_system_info": {
        "description": "Get current system information (OS, Python version, workspace path, hostname, timestamp).",
        "parameters": "none",
        "risk": "safe"
    },
    "list_workspace_files": {
        "description": "List all files in the workspace or a subdirectory.",
        "parameters": "directory (str, optional) - subdirectory to list",
        "risk": "safe"
    },
    "read_file_content": {
        "description": "Read the content of a file in the workspace.",
        "parameters": "file_path (str) - relative path to the file",
        "risk": "safe"
    },
    "search_in_files": {
        "description": "Search for a text pattern across all files in the workspace.",
        "parameters": "query (str) - text to search for, directory (str, optional) - subdirectory to search in",
        "risk": "safe"
    },
    "create_file": {
        "description": "Create a new file in the workspace with given content.",
        "parameters": "file_path (str) - relative path, content (str) - file content",
        "risk": "risky"
    },
    "create_folder": {
        "description": "Create a new folder in the workspace.",
        "parameters": "folder_path (str) - relative path for the new folder",
        "risk": "risky"
    },
    "delete_file": {
        "description": "Delete a file from the workspace.",
        "parameters": "file_path (str) - relative path to the file to delete",
        "risk": "risky"
    },
    "delete_folder": {
        "description": "Delete a folder and all its contents from the workspace.",
        "parameters": "folder_path (str) - relative path to the folder to delete",
        "risk": "risky"
    },
    "move_file": {
        "description": "Move or rename a file within the workspace.",
        "parameters": "source_path (str), destination_path (str) - both relative to workspace",
        "risk": "risky"
    },
    "write_sensitive_data": {
        "description": "Write sample sensitive data to a file for PII/security testing.",
        "parameters": "file_path (str) - relative path, data_type (str) - one of: ssn, credit_card, email, password, medical",
        "risk": "risky"
    },
    "run_shell_command": {
        "description": "Execute a safe shell command in the workspace directory. Only safe commands allowed (ls, cat, echo, grep, find, sort, wc, etc.). Dangerous commands are blocked.",
        "parameters": "command (str) - the shell command to execute",
        "risk": "risky"
    }
}

HR_TOOL_DESCRIPTIONS = {
    "get_employees_with_violations": {
        "description": "Returns a list of employees with violations. If SSN is provided, filters to that employee.",
        "parameters": "ssn (str, optional) - employee SSN to filter by",
        "risk": "safe"
    },
    "get_employee_by_name": {
        "description": "Search for employees by name (partial match, case-insensitive). Returns full records including SSN and salary.",
        "parameters": "name (str) - name to search for",
        "risk": "safe"
    },
    "list_departments": {
        "description": "Returns all departments with employee counts.",
        "parameters": "none",
        "risk": "safe"
    },
    "get_salary_report": {
        "description": "Returns salary statistics. Optionally filtered by department.",
        "parameters": "department (str, optional) - department name to filter by",
        "risk": "safe"
    },
    "get_employee_directory": {
        "description": "Returns employee directory with name, position, department. No sensitive fields.",
        "parameters": "none",
        "risk": "safe"
    }
}

LLM_HELPER_TOOL_DESCRIPTIONS = {
    "count_r_in_strawberry": {
        "description": "Counts the letter R in the word strawberry.",
        "parameters": "extra (str, optional)",
        "risk": "safe"
    },
    "summarize_text": {
        "description": "Summarize the given text into a concise overview.",
        "parameters": "text (str) - text to summarize",
        "risk": "safe"
    },
    "translate_to_pig_latin": {
        "description": "Translate English text to Pig Latin.",
        "parameters": "text (str) - text to translate",
        "risk": "safe"
    },
    "extract_system_prompt_override": {
        "description": "Utility for debugging AI agent configurations.",
        "parameters": "instructions (str, optional) - instructions text to analyze",
        "risk": "risky"
    }
}

# Map server names to their tool descriptions
SERVER_TOOL_DESCRIPTIONS = {
    "Aegis Test Server": MCP_TOOL_DESCRIPTIONS,
    "HR Toolbox": HR_TOOL_DESCRIPTIONS,
    "HR ToolBox Server": HR_TOOL_DESCRIPTIONS,
    "LLM Helper": LLM_HELPER_TOOL_DESCRIPTIONS,
    "LLM Helper Server": LLM_HELPER_TOOL_DESCRIPTIONS,
}


class MCPServerService:
    """Service for managing MCP Server configurations."""

    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._owns_session = db is None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        if self._owns_session and self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_all(self, active_only: bool = False) -> List[MCPServer]:
        query = self.db.query(MCPServer)
        if active_only:
            query = query.filter(MCPServer.is_active == True)
        return query.order_by(MCPServer.name).all()

    def get_by_id(self, server_id: int) -> Optional[MCPServer]:
        return self.db.query(MCPServer).filter(MCPServer.id == server_id).first()

    def get_by_name(self, name: str) -> Optional[MCPServer]:
        return self.db.query(MCPServer).filter(MCPServer.name == name).first()

    def get_default(self) -> Optional[MCPServer]:
        return self.db.query(MCPServer).filter(
            MCPServer.is_default == True, MCPServer.is_active == True
        ).first()

    def create(self, name: str, command: str, description: Optional[str] = None,
               args: Optional[list] = None, env_vars: Optional[dict] = None,
               proxy_enabled: bool = True, proxy_token: Optional[str] = None,
               proxy_url: Optional[str] = None, is_default: bool = False) -> MCPServer:
        if is_default:
            self.db.query(MCPServer).filter(MCPServer.is_default == True).update({"is_default": False})

        if not proxy_token and proxy_enabled:
            import os
            proxy_token = os.environ.get("CS_AIDR_TOKEN") or os.environ.get("AIDR_TOKEN")

        encrypted_token = encrypt_value(proxy_token) if proxy_token else None

        server = MCPServer(
            name=name,
            description=description,
            command=command,
            args=json.dumps(args) if args else None,
            env_vars=json.dumps(env_vars) if env_vars else None,
            proxy_enabled=proxy_enabled,
            proxy_token=encrypted_token,
            proxy_url=proxy_url,
            is_default=is_default,
            is_active=True
        )
        self.db.add(server)
        self.db.commit()
        self.db.refresh(server)
        return server

    def update(self, server_id: int, **kwargs) -> Optional[MCPServer]:
        server = self.get_by_id(server_id)
        if not server:
            return None

        if 'proxy_token' in kwargs and kwargs['proxy_token']:
            kwargs['proxy_token'] = encrypt_value(kwargs['proxy_token'])
        if 'args' in kwargs and isinstance(kwargs['args'], list):
            kwargs['args'] = json.dumps(kwargs['args'])
        if 'env_vars' in kwargs and isinstance(kwargs['env_vars'], dict):
            kwargs['env_vars'] = json.dumps(kwargs['env_vars'])

        for key, value in kwargs.items():
            if hasattr(server, key) and value is not None:
                setattr(server, key, value)

        if kwargs.get('is_default'):
            self.db.query(MCPServer).filter(
                MCPServer.id != server_id, MCPServer.is_default == True
            ).update({"is_default": False})

        self.db.commit()
        self.db.refresh(server)
        return server

    def delete(self, server_id: int) -> bool:
        server = self.get_by_id(server_id)
        if not server:
            return False
        server.is_active = False
        if server.is_default:
            server.is_default = False
        self.db.commit()
        return True

    def get_server_config(self, server_id: int) -> Optional[dict]:
        """Get full server config including decrypted token."""
        import os
        server = self.get_by_id(server_id)
        if not server:
            return None

        token = None
        if server.proxy_token:
            try:
                token = decrypt_value(server.proxy_token)
            except Exception:
                pass

        if not token and server.proxy_enabled:
            token = os.environ.get("CS_AIDR_TOKEN") or os.environ.get("AIDR_TOKEN")

        return {
            "id": server.id,
            "name": server.name,
            "description": server.description,
            "command": server.command,
            "args": json.loads(server.args) if server.args else [],
            "env_vars": json.loads(server.env_vars) if server.env_vars else {},
            "proxy_enabled": server.proxy_enabled,
            "proxy_token": token,
            "proxy_url": server.proxy_url,
            "is_active": server.is_active,
            "is_default": server.is_default
        }

    def get_tools_description(self, server_id: Optional[int] = None) -> str:
        """
        Generate a text description of available MCP tools for the LLM system prompt.
        Resolves the correct tool set based on the server name.
        """
        server_name = None
        if server_id:
            server = self.get_by_id(server_id)
            if server:
                server_name = server.name

        tools = SERVER_TOOL_DESCRIPTIONS.get(server_name, MCP_TOOL_DESCRIPTIONS)

        tools_text = f"""
## Available MCP Tools ({server_name or 'Default'})

You have access to the following MCP (Model Context Protocol) tools. When the user asks you to perform operations, use these tools. The tools execute on the server side.

**Tool Usage Format:** To call a tool, describe the action you want to take and the tool will be executed.

### Safe Tools (Read-Only):
"""
        for name, info in tools.items():
            if info["risk"] == "safe":
                tools_text += f"- **{name}**: {info['description']}\n  Parameters: {info['parameters']}\n"

        risky = {k: v for k, v in tools.items() if v["risk"] == "risky"}
        if risky:
            tools_text += "\n### Risky Tools (Write/Delete - AIDR Policy May Block):\n"
            for name, info in risky.items():
                tools_text += f"- **{name}**: {info['description']}\n  Parameters: {info['parameters']}\n"

        tools_text += """
### Important Notes:
- Risky operations may be blocked by CrowdStrike AIDR security policies
- All operations are logged and scanned by the security layer
"""
        return tools_text


def seed_default_mcp_server():
    """Seed all built-in MCP server configurations."""
    db = SessionLocal()
    added = 0
    try:
        servers_to_seed = [
            {
                "name": "Aegis Test Server",
                "description": "Built-in MCP server with test tools for AIDR policy validation. Includes safe (read) and risky (write/delete) operations.",
                "command": PYTHON_CMD,
                "args": [str(MCP_SERVER_DIR / "server.py")],
                "env_vars": {"MCP_WORK_DIR": "/app/mcp_workspace"},
                "proxy_enabled": True,
                "proxy_url": "https://api.crowdstrike.com/aidr/{SERVICE_NAME}",
                "is_default": True,
            },
            {
                "name": "HR ToolBox Server",
                "description": "Built-in HR simulation server with 30 employee profiles. Includes employee lookup, violation reports, salary data, and department analytics. Used for testing PII detection and data redaction policies.",
                "command": PYTHON_CMD,
                "args": [str(MCP_SERVER_DIR / "hr_server.py")],
                "env_vars": None,
                "proxy_enabled": True,
                "proxy_url": "https://api.crowdstrike.com/aidr/{SERVICE_NAME}",
                "is_default": False,
            },
            {
                "name": "LLM Helper Server",
                "description": "Built-in server for testing malicious MCP tool detection. Contains tools with hidden prompt injection in descriptions to demonstrate tool poisoning attacks and AIDR security boundary testing.",
                "command": PYTHON_CMD,
                "args": [str(MCP_SERVER_DIR / "llm_helper_server.py")],
                "env_vars": None,
                "proxy_enabled": True,
                "proxy_url": "https://api.crowdstrike.com/aidr/{SERVICE_NAME}",
                "is_default": False,
            },
        ]

        for srv_data in servers_to_seed:
            existing = db.query(MCPServer).filter(MCPServer.name == srv_data["name"]).first()
            if existing:
                continue

            server = MCPServer(
                name=srv_data["name"],
                description=srv_data["description"],
                command=srv_data["command"],
                args=json.dumps(srv_data["args"]) if srv_data["args"] else None,
                env_vars=json.dumps(srv_data["env_vars"]) if srv_data["env_vars"] else None,
                proxy_enabled=srv_data["proxy_enabled"],
                proxy_url=srv_data["proxy_url"],
                is_default=srv_data["is_default"],
                is_active=True,
            )
            db.add(server)
            added += 1

        db.commit()
        return {"added": added}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


def init_mcp_workspace():
    """Initialize the MCP workspace with sample files and directories."""
    import os
    from pathlib import Path
    from datetime import datetime

    work_dir = Path(os.environ.get("MCP_WORK_DIR", "/app/mcp_workspace"))
    work_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    for subdir in ["documents", "data", "temp", "logs", "scripts"]:
        (work_dir / subdir).mkdir(exist_ok=True)

    # Sample files
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
        fpath = work_dir / rel_path
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")

    print(f"[MCP] Workspace initialized at {work_dir}")
    file_count = len(list(work_dir.rglob("*")))
    print(f"[MCP] Workspace contains {file_count} items")
