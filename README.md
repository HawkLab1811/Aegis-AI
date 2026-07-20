# Aegis AI - Secure AI Gateway

Aegis AI is a security-first AI gateway that provides **CrowdStrike AIDR-protected** access to multiple LLM providers. It acts as a proxy between users and AI models, scanning all inputs and outputs through CrowdStrike's AI Detection and Response (AIDR) service.

---

## Features

### Multi-Provider LLM Support
Pre-configured adapters for 17 models across 5 providers:
- **OpenAI** - GPT-5, GPT-5 Mini, GPT-5 Nano, GPT-4o (Vision), GPT-4o Mini
- **Anthropic** - Claude Opus 4.5, Claude Sonnet 4.5, Claude Haiku 4.5
- **Google** - Gemini 3 Flash, Gemini 3 Pro, Gemini 2.5 Flash, Gemini 2.5 Pro
- **xAI** - Grok 4.1 Fast, Grok 4 (Latest), Grok Code Fast
- **Xiaomi MiMo** - MiMo V2.5 Pro, MiMo V2.5

### CrowdStrike AIDR Security
- Real-time input/output scanning through CrowdStrike AI Guard
- Configurable AIDR collectors with per-deployment tokens
- Access rule enforcement, content blocking, and content transformation
- MCP tool scanning via CrowdStrike AIDR MCP Proxy

### Built-in MCP Servers (3 servers, 20 tools)
- **Aegis Test Server** - File operations (safe + risky) for AIDR policy validation
- **HR ToolBox Server** - 30 employee profiles with PII (SSN, salary) for data redaction testing
- **LLM Helper Server** - Malicious tool descriptions for prompt injection detection testing

### RAG Knowledge Base
- ChromaDB vector store with per-knowledge-base isolation
- Support for: PDF, TXT, MD, Images, Videos, Excel, CSV, Word, PowerPoint
- Vision-powered media description (images/video described by LLM, then vectorized)
- Automatic vision provider selection from configured engines

### Conversation Management
- Persistent chat history per user
- Multi-conversation support with create/switch/delete
- Context-aware title generation

### First Deployment Wizard
A guided 4-step setup that runs on first launch:
1. **Admin Password** - Create administrator credentials (stored hashed in DB)
2. **AIDR Configuration** - Set CrowdStrike AIDR collector token and URL
3. **MCP Proxy** - Configure CrowdStrike MCP proxy settings
4. **AI Engine** - Select a provider and enter API key

### Additional Features
- Profile system for saving configuration presets
- Internal test repository with 36 AIDR policy testing samples
- Fernet encryption for all API keys and tokens at rest
- Database-backed authentication (no .env dependency for passwords)
- Auto-generated encryption key at runtime

---

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose)
- A CrowdStrike AIDR token ([learn more](https://www.crowdstrike.com/products/ai-guard/))
- An API key from at least one supported LLM provider

### Clone and Build

```bash
git clone https://github.com/HawkLab1811/Aegis-AI.git
cd aegis-ai
cp .env.example .env
docker-compose up -d
```

### First Launch

1. Open **http://localhost:15000** in your browser
2. The **Setup Wizard** will appear automatically
3. Follow the 4 steps:
   - Set your admin password (minimum 8 characters)
   - Enter your CrowdStrike AIDR token and API URL
   - Configure MCP proxy settings (optional)
   - Select an AI engine and enter your API key
4. Start chatting through the secure AI gateway

### Custom Port

To run on a different port, edit `.env` before starting:

```bash
AEGIS_PORT=8080
```

---

## Architecture

```
User Request
    |
    v
FastAPI Backend (port 15000)
    |
    v
+--> AIDR Input Scan (CrowdStrike AI Guard)
|       |
|       v (if allowed)
|   RAG Context Retrieval (ChromaDB)
|       |
|       v
|   LLM Generation (OpenAI / Anthropic / Google / xAI / MiMo)
|       |
|       v
|   MCP Tool Execution (if agent has MCP server)
|       |
|       v
+-- AIDR Output Scan (CrowdStrike AI Guard)
    |
    v
Response to User
```

### Data Persistence
All data is stored in Docker volumes:
- `aegis-data` - SQLite database, RAG files, ChromaDB vectors
- `mcp-workspace` - MCP server sandboxed workspace

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AEGIS_PORT` | No | `15000` | Host port for the web interface |
| `ENCRYPTION_KEY` | No | Auto-generated | Fernet key for encrypting API keys |
| `CS_AIDR_TOKEN` | No | - | CrowdStrike AIDR token (can be set via wizard) |
| `CS_AIDR_BASE_URL_TEMPLATE` | No | `https://api.crowdstrike.com/aidr/{SERVICE_NAME}` | AIDR API URL template |

### Security Notes
- Admin password is stored as a salted SHA-256 hash in the database
- All API keys and tokens are encrypted with Fernet before storage
- The `.env` file is excluded from the Docker image via `.dockerignore`
- No secrets are hardcoded in source code
- The encryption key is auto-generated at first run if not provided

---

## MCP Server Configuration

Aegis AI includes 3 pre-configured MCP servers that are automatically seeded on first run. Each server can be toggled between proxy mode (routed through CrowdStrike AIDR MCP proxy) and direct mode.

| Server | Purpose | Tools |
|--------|---------|-------|
| Aegis Test Server | AIDR policy validation | 11 tools (file ops, shell, data writing) |
| HR ToolBox Server | PII detection testing | 5 tools (employee lookup, salary reports) |
| LLM Helper Server | Prompt injection testing | 4 tools (including hidden injection) |

---

## Updating

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Data in Docker volumes persists across updates.

## Reset

To start with a completely fresh database:

```bash
docker-compose down -v
docker-compose up -d
```

The Setup Wizard will appear again on next launch.

---

## License

See LICENSE file for details.
