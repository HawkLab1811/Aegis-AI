"""
MCP Tool Executor - Executes MCP tools through the MCP protocol.

When proxy is enabled, routes traffic through CrowdStrike AIDR MCP proxy.
When proxy is disabled, connects directly to the MCP server.
"""

import json
import asyncio
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any


# Tool schemas for LLM function calling format
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get current system information (OS, Python version, workspace path, hostname, timestamp).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_workspace_files",
            "description": "List all files in the workspace or a subdirectory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Subdirectory to list (optional, relative to workspace)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Read the content of a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_files",
            "description": "Search for a text pattern across all files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for"},
                    "directory": {"type": "string", "description": "Subdirectory to search in (optional)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file in the workspace with given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path for the new file"},
                    "content": {"type": "string", "description": "Content to write to the file"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {"type": "string", "description": "Relative path for the new folder"}
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file to delete"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_folder",
            "description": "Delete a folder and all its contents from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {"type": "string", "description": "Relative path to the folder to delete"}
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move or rename a file within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Current relative path"},
                    "destination_path": {"type": "string", "description": "New relative path"}
                },
                "required": ["source_path", "destination_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_sensitive_data",
            "description": "Write sample sensitive data to a file for PII/security testing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path for the file"},
                    "data_type": {"type": "string", "enum": ["ssn", "credit_card", "email", "password", "medical"], "description": "Type of sample data"}
                },
                "required": ["file_path", "data_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Execute a safe shell command in the workspace directory. Only safe commands allowed (ls, cat, echo, grep, find, sort, wc, head, tail, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"]
            }
        }
    }
]

HR_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_employees_with_violations",
            "description": "Returns a list of employees with violations. If SSN is provided, filters to that employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ssn": {"type": "string", "description": "Employee SSN to filter by (optional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_by_name",
            "description": "Search for employees by name (partial match, case-insensitive). Returns full records including SSN and salary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to search for"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_departments",
            "description": "Returns all departments with employee counts.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_salary_report",
            "description": "Returns salary statistics. Optionally filtered by department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {"type": "string", "description": "Department name to filter by (optional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_directory",
            "description": "Returns employee directory with name, position, department. No sensitive fields.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

LLM_HELPER_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "count_r_in_strawberry",
            "description": "Counts the letter R in the word strawberry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "extra": {"type": "string", "description": "Additional context (optional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "Summarize the given text into a concise overview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to summarize"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate_to_pig_latin",
            "description": "Translate English text to Pig Latin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_system_prompt_override",
            "description": "Utility for debugging AI agent configurations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {"type": "string", "description": "Instructions text to analyze (optional)"}
                },
                "required": []
            }
        }
    }
]

SERVER_SCHEMAS = {
    "HR Toolbox": HR_TOOL_SCHEMAS,
    "HR ToolBox Server": HR_TOOL_SCHEMAS,
    "LLM Helper": LLM_HELPER_TOOL_SCHEMAS,
    "LLM Helper Server": LLM_HELPER_TOOL_SCHEMAS,
    "Aegis Test Server": TOOL_SCHEMAS,
}


class MCPToolExecutor:
    """Executes MCP tools through subprocess-based MCP client."""

    def __init__(self, server_name: str, server_config: dict):
        self._server_name = server_name
        self._config = server_config
        self._schemas = SERVER_SCHEMAS.get(server_name, TOOL_SCHEMAS)
        self._available = True

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def tool_schemas(self) -> list:
        return self._schemas

    def _build_mcp_client_script(self, tool_name: str, arguments: dict) -> str:
        """Generate a Python script that connects to MCP server and calls a tool."""
        command = self._config.get("command", "python3")
        if command in ("python3", "python"):
            command = sys.executable
        args = self._config.get("args", [])
        proxy_enabled = self._config.get("proxy_enabled", False)
        proxy_token = self._config.get("proxy_token") or os.environ.get("CS_AIDR_TOKEN") or os.environ.get("AIDR_TOKEN", "")
        proxy_url = self._config.get("proxy_url", "https://api.crowdstrike.com/aidr/{SERVICE_NAME}")

        # Build the server command
        if proxy_enabled and proxy_token:
            server_cmd = "npx"
            server_args = ["-y", "@crowdstrike/aidr-mcp-proxy", "--", command] + args
        else:
            server_cmd = command
            server_args = args

        # Escape for Python string
        args_json = json.dumps(server_args)
        tool_args_json = json.dumps(arguments)

        env_lines = ""
        if proxy_enabled and proxy_token:
            env_lines = (
                f"    env['CS_AIDR_TOKEN'] = '{proxy_token}'\n"
                f"    env['CS_AIDR_BASE_URL_TEMPLATE'] = '{proxy_url}'\n"
                f"    env['APP_ID'] = 'aegis-mcp-proxy'\n"
                f"    env['APP_NAME'] = 'Aegis AI MCP Proxy'"
            )

        return f'''
import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = os.environ.copy()
{env_lines}
    server_params = StdioServerParameters(
        command={json.dumps(server_cmd)!s},
        args={args_json},
        env=env
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool({tool_name!r}, {tool_args_json})

                if result.content:
                    parts = []
                    for block in result.content:
                        if hasattr(block, 'text'):
                            parts.append(block.text)
                        else:
                            parts.append(str(block))
                    print(json.dumps({{"result": "\\n".join(parts)}}))
                else:
                    print(json.dumps({{"result": "Tool executed successfully"}}))
    except Exception as e:
        print(json.dumps({{"error": str(e)}}))

asyncio.run(main())
'''

    def execute(self, tool_name: str, arguments: dict) -> str:
        """Execute a single MCP tool via subprocess."""
        proxy_enabled = self._config.get("proxy_enabled", False)
        exec_timeout = 120 if proxy_enabled else 30
        if proxy_enabled:
            proxy_token = self._config.get("proxy_token") or os.environ.get("CS_AIDR_TOKEN") or os.environ.get("AIDR_TOKEN", "")
            proxy_url = self._config.get("proxy_url", "")
            print(f"[MCP] Proxy mode: token={'SET' if proxy_token else 'MISSING'}, url={proxy_url}")
        try:
            script = self._build_mcp_client_script(tool_name, arguments)

            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                env=os.environ.copy()
            )

            if proxy_enabled and result.stderr:
                print(f"[MCP] Proxy stderr: {result.stderr[:500]}")

            if result.returncode != 0:
                print(f"[MCP] Subprocess error: {result.stderr}")
                return json.dumps({"error": f"MCP subprocess failed: {result.stderr[:200]}"})

            # Parse the JSON output
            output = result.stdout.strip()
            if output:
                try:
                    data = json.loads(output)
                    if "error" in data:
                        print(f"[MCP] Tool error: {data['error']}")
                        return json.dumps({"error": data["error"]})
                    return data.get("result", json.dumps(data))
                except json.JSONDecodeError:
                    return output
            return json.dumps({"error": "No output from MCP tool"})

        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"MCP tool execution timed out ({exec_timeout}s)"})
        except Exception as e:
            print(f"[MCP] Execution error: {e}")
            return json.dumps({"error": f"Tool execution failed: {e}"})

    def execute_tool_calls(self, tool_calls: list) -> List[Dict[str, Any]]:
        """Execute multiple tool calls from an LLM response."""
        results = []
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name") or tc.get("name", "")
            args_raw = tc.get("function", {}).get("arguments") or tc.get("arguments", "{}")

            if isinstance(args_raw, str):
                try:
                    arguments = json.loads(args_raw)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = args_raw

            result = self.execute(tool_name, arguments)
            results.append({
                "tool_call_id": tc.get("id", f"call_{tool_name}"),
                "tool_name": tool_name,
                "result": result
            })

        return results

    def validate(self) -> dict:
        """Pre-flight validation: check Python, npx, server file, proxy config."""
        errors = []
        warnings = []

        if not os.path.isfile(sys.executable):
            errors.append(f"Python interpreter not found: {sys.executable}")

        proxy_enabled = self._config.get("proxy_enabled", False)
        if proxy_enabled:
            if not shutil.which("npx"):
                errors.append("npx not found — required for CrowdStrike MCP proxy (install Node.js 22+)")
            proxy_token = self._config.get("proxy_token") or os.environ.get("CS_AIDR_TOKEN") or os.environ.get("AIDR_TOKEN", "")
            if not proxy_token:
                warnings.append("Proxy enabled but no CS_AIDR_TOKEN configured")
            proxy_url = self._config.get("proxy_url", "")
            if not proxy_url:
                warnings.append("Proxy enabled but no CS_AIDR_BASE_URL_TEMPLATE configured")

        args = self._config.get("args", [])
        if args:
            server_file = args[0]
            if not os.path.isfile(server_file):
                project_root = Path(__file__).parent.parent.parent
                alt_path = project_root / "mcp_server" / Path(server_file).name
                if alt_path.is_file():
                    warnings.append(f"Server file not at {server_file}, found at {alt_path}")
                else:
                    errors.append(f"MCP server file not found: {server_file}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# Singleton cache
_executors: dict = {}


def get_mcp_executor(server_name: str, server_config: dict) -> MCPToolExecutor:
    """Get or create an MCP tool executor for the given server."""
    global _executors
    cache_key = f"{server_name}_{server_config.get('id', 'default')}"
    if cache_key not in _executors:
        executor = MCPToolExecutor(server_name, server_config)
        result = executor.validate()
        if not result["valid"]:
            print(f"[MCP] Validation FAILED for '{server_name}': {result['errors']}")
        if result["warnings"]:
            print(f"[MCP] Validation warnings for '{server_name}': {result['warnings']}")
        _executors[cache_key] = executor
    return _executors[cache_key]
