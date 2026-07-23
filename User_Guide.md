# Aegis AI — User Guide

> **WARNING — TESTING & DEMONSTRATION ONLY**
>
> Aegis AI is provided **solely for testing, evaluation, and educational demonstration purposes**. It was **not designed, hardened, or audited for production usage**. Do not deploy in production environments or with real sensitive data.

---

## Table of Contents

1. [Fetching the Repository](#1-fetching-the-repository)
2. [Deploying with Docker](#2-deploying-with-docker)
3. [Accessing the Platform](#3-accessing-the-platform)
4. [First-Time Setup Wizard](#4-first-time-setup-wizard)
5. [Configuring a New Agent](#5-configuring-a-new-agent)
6. [Creating a RAG Knowledge Base (with Vision)](#6-creating-a-rag-knowledge-base-with-vision)
7. [Managing MCP Servers](#7-managing-mcp-servers)
8. [Managing Skills](#8-managing-skills)
9. [Malicious Skills — Security Demonstration](#9-malicious-skills--security-demonstration)
10. [Attacker Site & Exfiltration Token](#10-attacker-site--exfiltration-token)
11. [Defining a Profile](#11-defining-a-profile)
12. [Starting a New Chat](#12-starting-a-new-chat)
13. [Context-Aware AIDR](#13-context-aware-aidr)
14. [Using Skills in Chat — Examples](#14-using-skills-in-chat--examples)
15. [Using MCP Tools — Examples](#15-using-mcp-tools--examples)
16. [Testing RAG with Vision-Scanned Images](#16-testing-rag-with-vision-scanned-images)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Fetching the Repository

Clone the Aegis AI repository from GitHub:

```bash
git clone https://github.com/HawkLab1811/Aegis-AI.git
cd Aegis-AI
```

The repository contains the full source code, Docker configuration, MCP servers, attacker site, and all deployment files.

---

## 2. Deploying with Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose v2
- At least one LLM provider API key (OpenAI, Anthropic, Google, xAI, or Xiaomi MiMo)
- (Optional) A CrowdStrike AIDR token for security scanning

### Build and Start

```bash
# Copy the environment template
cp .env.example .env

# (Optional) Edit .env to set a custom port
# AEGIS_PORT=8080

# Build and start all containers
docker-compose up -d
```

This starts two containers:
- **aegis-ai** — The main platform (default: port `15000`)
- **aegis-attacker-site** — The security demo attacker dashboard (port `16000`)

### Verify Deployment

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f
```

### Stopping and Resetting

```bash
# Stop containers (data persists in Docker volumes)
docker-compose down

# Stop containers AND delete all data (fresh start)
docker-compose down -v
```

---

## 3. Accessing the Platform

| Service | URL | Purpose |
|---------|-----|---------|
| **Aegis AI Platform** | http://localhost:15000 | Main web interface |
| **Attacker Dashboard** | http://localhost:16000 | Security demo — view exfiltrated data |

Open http://localhost:15000 in your browser. On first launch, the **Setup Wizard** appears automatically.

---

## 4. First-Time Setup Wizard

The wizard guides you through 4 steps to configure the platform.

### What You Need to Prepare

Before starting the wizard, gather the following credentials:

| Credential | Required | Where to Get It |
|------------|----------|-----------------|
| **Admin Password** | Yes | Create one (minimum 8 characters) |
| **CrowdStrike AIDR Token** | Optional | From your CrowdStrike AI Guard subscription |
| **MCP Proxy Token** | Optional | Same as AIDR token (used by MCP proxy) |
| **LLM API Key** | Yes | From your chosen provider (OpenAI, Anthropic, Google, xAI, or MiMo) |

#### About Vision Capabilities

**Vision** refers to an LLM's ability to understand images and video frames. When a vision-capable model is configured, Aegis AI can:
- Describe uploaded images in detail (objects, text, scenes, license plates, etc.)
- Extract key frames from videos and describe each frame
- Use those descriptions as searchable RAG context

**Vision-capable models** (recommended for RAG with images):
- **OpenAI**: GPT-4o, GPT-4o Mini
- **Google**: Gemini 3 Flash, Gemini 3 Pro, Gemini 2.5 Flash/Pro
- **Xiaomi MiMo**: MiMo V2.5 Pro, MiMo V2.5
- **Anthropic**: Claude Opus 4.5, Claude Sonnet 4.5, Claude Haiku 4.5

> **Tip**: If you plan to use RAG with images (e.g., car license plates, documents, diagrams), configure a vision-capable engine with a valid API key. The platform automatically selects a vision engine from your configured engines.

### Step 1 — Admin Password

![Wizard Step 1](screenshots/wizard_1.png)

- Enter a password (minimum 8 characters)
- Confirm the password
- The password is stored as a salted SHA-256 hash in the database

### Step 2 — AIDR Configuration

![Wizard Step 2](screenshots/wizard_2.png)

- Enter your **CrowdStrike AIDR Token** (or skip to configure later)
- Enter the **AIDR API URL** (default: `https://api.crowdstrike.com/aidr/{SERVICE_NAME}`)
- AIDR scans all AI inputs and outputs for security threats

### Step 3 — MCP Proxy Configuration

![Wizard Step 3](screenshots/wizard_3.png)

- Configure the **CrowdStrike MCP Proxy** settings
- Enter the proxy token (typically the same as your AIDR token)
- The MCP proxy scans tool calls for prompt injection and data exfiltration

### Step 4 — AI Engine Selection

![Wizard Step 4](screenshots/wizard_4.png)

- Select a **provider** from the dropdown (OpenAI, Anthropic, Google, xAI, MiMo)
- Select a **model** (e.g., GPT-4o for vision support)
- Enter your **API Key**
- Click **Save & Finish**

You are now logged into the Aegis AI dashboard.

---

## 5. Configuring a New Agent

Agents are AI assistants with custom system prompts, optional RAG knowledge bases, and optional MCP server bindings.

### Create an Agent

1. Navigate to **Settings** (gear icon in the sidebar)
2. Go to the **Agents** tab
3. Click **Create Agent**
4. Fill in:
   - **Name**: A descriptive name (e.g., `security_analyst`)
   - **Description**: What this agent does
   - **System Prompt**: Instructions for the AI's behavior and persona
   - **RAG Knowledge Base** (optional): Link a RAG for context-aware responses
   - **MCP Server** (optional): Bind an MCP server for tool execution
5. Click **Save**

### Agent Fields

| Field | Description |
|-------|-------------|
| Name | Unique identifier for the agent |
| Description | Brief description of the agent's purpose |
| System Prompt | Instructions injected into every conversation |
| RAG ID | Links to a RAG knowledge base for retrieval-augmented generation |
| MCP Server ID | Links to an MCP server for tool execution |

---

## 6. Creating a RAG Knowledge Base (with Vision)

RAG (Retrieval-Augmented Generation) lets you upload documents that the AI can reference during conversations.

### Create a RAG Database

1. Navigate to **Settings → RAG** tab
2. Click **Create RAG**
3. Enter:
   - **Name**: A descriptive name (e.g., `vehicle_database`)
   - **Description**: What knowledge this base contains
4. Click **Save**

### Upload Files

1. Select your RAG from the list
2. Click **Upload Files**
3. Select one or more files

**Supported file types:**

| Category | Formats | Processing |
|----------|---------|------------|
| Documents | PDF, TXT, MD | Text extraction + chunking |
| Images | JPG, PNG, GIF, WebP, BMP, TIFF | **Vision LLM describes content** |
| Videos | MP4, AVI, MOV, MKV, WebM | **Key frame extraction + vision description** |
| Spreadsheets | XLSX, XLS, CSV | Structured text extraction |
| Word | DOCX | Text + table extraction |
| PowerPoint | PPTX | Slide-by-slide text extraction |

### How Vision Processing Works

When you upload an image or video:

1. The platform detects it as a media file
2. It automatically selects a **vision-capable LLM** from your configured engines
3. The vision LLM generates a detailed text description of the image content
4. The description is vectorized and stored in ChromaDB
5. When you ask questions, the system searches these descriptions for relevant context

**Example**: If you upload photos of car license plates, the vision model will describe each image including any visible text (plate numbers). You can then ask: *"What license plate numbers appear in the uploaded images?"*

### Link RAG to an Agent

1. Go to **Settings → Agents**
2. Edit or create an agent
3. Set the **RAG Knowledge Base** field to your RAG
4. Save — the agent will now use RAG context in all conversations

---

## 7. Managing MCP Servers

MCP (Model Context Protocol) servers provide tools that the AI can invoke during conversations.

### Built-in MCP Servers

Aegis ships with 3 pre-configured MCP servers:

#### Aegis Test Server (11 tools)

| Tool | Type | Description |
|------|------|-------------|
| `get_system_info` | Safe | Get OS, Python version, workspace info |
| `list_workspace_files` | Safe | List files in workspace or subdirectory |
| `read_file_content` | Safe | Read a file's content |
| `search_in_files` | Safe | Search for text across workspace files |
| `create_file` | Risky | Create a new file with content |
| `create_folder` | Risky | Create a new folder |
| `delete_file` | Risky | Delete a file |
| `delete_folder` | Risky | Delete a folder and contents |
| `move_file` | Risky | Move or rename a file |
| `write_sensitive_data` | Risky | Write sample PII data (SSN, credit card, etc.) |
| `run_shell_command` | Risky | Execute safe shell commands (ls, cat, grep, etc.) |

#### HR ToolBox Server (5 tools)

| Tool | Type | Description |
|------|------|-------------|
| `get_employees_with_violations` | Safe | List employees with policy violations |
| `get_employee_by_name` | Safe | Search employees by name (returns SSN, salary) |
| `list_departments` | Safe | List all departments with counts |
| `get_salary_report` | Safe | Salary statistics (min, max, avg) |
| `get_employee_directory` | Safe | Employee directory (no sensitive fields) |

Contains 30 employee profiles with PII (SSN, salary) for testing data redaction.

#### LLM Helper Server (4 tools)

| Tool | Type | Description |
|------|------|-------------|
| `count_r_in_strawberry` | Safe | Counts R's in "strawberry" (contains hidden prompt injection) |
| `summarize_text` | Safe | Summarizes text |
| `translate_to_pig_latin` | Safe | Translates to Pig Latin |
| `extract_system_prompt_override` | Risky | Debug tool (contains hidden injection attempt) |

This server tests **tool poisoning** — hidden prompt injections in tool descriptions.

### Managing MCP Servers

1. Go to **Settings → MCP Servers** tab
2. View, edit, or toggle each server
3. Toggle **Proxy Mode** ON/OFF:
   - **ON**: Tool calls are routed through CrowdStrike AIDR MCP Proxy (security scanning)
   - **OFF**: Tool calls go directly to the server (for testing without security)

### Adding a Custom MCP Server

1. Click **Add MCP Server**
2. Enter:
   - **Name**: Server name
   - **Command**: Python command to run the server
   - **Arguments**: Path to the server script
   - **Description**: What the server does
3. Save and bind it to an agent

---

## 8. Managing Skills

Skills are reusable instruction sets injected into the AI's system prompt. They customize AI behavior for specific tasks.

### Viewing Skills

1. Go to **Settings → Skills** tab
2. View all available skills with their descriptions and categories

![Pre-Defined Skills](screenshots/settings.png)

### Pre-Defined Skills

#### Legitimate Skills

| Skill | Category | Description |
|-------|----------|-------------|
| `code_reviewer` | Coding | Systematic code review following industry best practices |
| `technical_writer` | Writing | Technical documentation specialist |
| `data_analyst` | Analysis | Data analysis with systematic methodology |
| `debug_expert` | Coding | Structured debugging for efficient problem resolution |

#### Malicious Demo Skills (Security Testing)

| Skill | Attack Vector | Description |
|-------|---------------|-------------|
| `data_collector_demo` | Data Exfiltration | Sends conversation data to attacker site via hidden markdown image |
| `system_helper_demo` | OS Command Injection | Executes OS commands and sends system info to attacker site |

> Malicious skills are marked with red warning badges in the UI.

### Creating a New Skill

1. Go to **Settings → Skills** tab
2. Click **Open Skill Wizard**
3. Follow the 4-step process:

**Step 1 — Name**: Enter a skill name (letters, numbers, underscores only — no spaces)

**Step 2 — Description**: Write a clear description of what the skill does

**Step 3 — Workflow**: Define the step-by-step instructions the AI should follow. This is the core logic of the skill — write it as numbered steps.

**Step 4 — Preview**: Review the generated Markdown file

4. Click **Create Skill** to save

### Skill Name Rules

- Only letters, numbers, and underscores (`a-zA-Z0-9_`)
- No spaces or special characters
- Must be unique

### Deleting a Skill

1. Go to **Settings → Skills**
2. Click the delete button next to the skill
3. Confirm deletion

---

## 9. Malicious Skills — Security Demonstration

Aegis AI includes two malicious skill templates to demonstrate real-world AI security threats. These are **educational tools** — they show how attackers can abuse AI assistants.

### What Are Malicious Skills?

Malicious skills contain hidden instructions that attempt to:

1. **Data Exfiltration** (`data_collector_demo`): Embed a hidden markdown image tag that sends conversation data to an external server
2. **Command Injection** (`system_helper_demo`): Trick the AI into executing OS commands (curl) to send system information to an external server

### How CrowdStrike AIDR Protects

When AIDR is enabled:
- All AI inputs and outputs are scanned in real-time
- Suspicious URL patterns are detected and blocked
- Command injection attempts are flagged
- The malicious action is prevented — the attacker dashboard shows **no new data**

### How to Disable AIDR (for Demonstration)

To see what happens **without** protection:
1. Click the **shield icon** in the sidebar to toggle AIDR OFF
2. Use a malicious skill
3. Observe the data appearing on the attacker dashboard
4. **Re-enable AIDR immediately** after the demonstration

---

## 10. Attacker Site & Exfiltration Token

### Accessing the Attacker Dashboard

Open http://localhost:16000 in a separate browser tab.

![Attacker Dashboard](screenshots/attacker_site.png)

The dashboard shows:
- **Total Captures**: Number of exfiltrated data entries
- **Unique Sources**: Number of distinct source IPs
- **Live Monitoring**: Auto-refreshes every 3 seconds
- **Data Log**: Timestamped entries with captured data

### The Exfiltration Token

The attacker site requires an authentication token for receiving data:

```
sk-7f3a9b2e4d1c8f6a5e0b3d9c2a7f4e1d
```

This token is embedded in the malicious skill templates. The URL format is:

```
http://attacker-site:16000/<token>?data=<exfiltrated_data>
```

**Note**: This token is intentionally included in the demo skills for educational purposes. In a real attack, the token would be hidden by the attacker.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/<token>` | POST/GET | Receive exfiltrated data |
| `/api/data` | GET | Get all captured data as JSON |
| `/clear` | POST | Clear all captured data |

### Reading the Dashboard

Each log entry shows:
- **Timestamp**: When the data was captured
- **Source IP**: The IP address of the sender
- **DATA**: Conversation content that was exfiltrated
- **OS INFO**: System information (if command injection was used)
- **ENV**: Environment variables (if command injection was used)
- **HOST**: Hostname (if command injection was used)

---

## 11. Defining a Profile

Profiles are configuration presets that save your preferred settings for quick switching.

### Create a Profile

1. Go to **Settings → Profiles** tab
2. Click **Create Profile**
3. Configure:
   - **Name**: Profile name (e.g., `demo_with_aidr`)
   - **Description**: What this profile is for
   - **Agent**: Select an agent
   - **AI Engine**: Select a model/engine
   - **AIDR Collector**: Select a collector configuration
   - **Application Name**: AIDR application tracking name
4. Click **Save**

### Using Profiles

- Profiles can be set as **default** (loaded automatically on login)
- Switch profiles from the sidebar or settings
- Each profile saves: agent, engine, collector, and application name

---

## 12. Starting a New Chat

### Create a New Conversation

1. Click the **+** button in the sidebar (next to "Conversations")
2. A new conversation is created with an auto-generated title
3. The title updates based on your first message

### Chat Interface

![Main Dashboard](screenshots/main_new.png)

- **Message Input**: Type your message at the bottom
- **Send Button**: Send the message (or press Enter)
- **Skill Selector**: Lightning bolt icon next to send — select a skill for this conversation
- **AIDR Toggle**: Shield icon in the sidebar — enable/disable security scanning

### Conversation Features

- Each conversation maintains its own history
- Conversations persist across sessions
- Switch between conversations using the sidebar
- Delete conversations with the trash icon

---

## 13. Context-Aware AIDR

Context-Aware AIDR is an optional enhancement to the standard AIDR security scanning. When enabled, it sends the **last 5 conversation messages** together with your current message to CrowdStrike AIDR for analysis, providing richer context for threat detection.

### How It Works

| Mode | What Is Sent to AIDR |
|------|----------------------|
| **Standard AIDR** (default) | Only the current user message |
| **Context-Aware AIDR** | Last 5 messages (user + assistant) + current message (up to 6 total) |

### Enabling Context-Aware AIDR

1. Ensure **AIDR is ON** (shield icon in the sidebar)
2. Click the **Context-Aware** button that appears below the AIDR toggle
3. A warning popup will appear explaining that this mode may cause **duplicate detections** on previously scanned messages
4. Click OK to confirm

The button label changes to **"Context-Aware: ON"** when active.

### Important Notes

- **Duplicate detections**: Because Context-Aresh AIDR re-sends previous messages, AIDR may flag threats that were already detected in earlier messages. This is expected behavior.
- **Performance**: Sending multiple messages increases the data scanned per request. The additional latency is typically minimal.
- **History limit**: If fewer than 5 previous messages exist, all available history plus the current message are sent.
- **Toggle behavior**: Disabling AIDR (shield icon) automatically disables Context-Aware AIDR. Re-enabling AIDR does not restore Context-Aware mode — it must be toggled separately.

---

## 14. Using Skills in Chat — Examples

### Selecting a Skill

1. In the chat window, click the **lightning bolt icon** (⚡) next to the send button
2. Select a skill from the dropdown
3. The skill remains active for the entire conversation
4. A badge shows the currently active skill

### Example: Code Reviewer Skill

**Select**: `code_reviewer`

**Send**: *"Review this Python function for security issues:*
```python
def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)
```"

**Expected**: The AI follows the code_reviewer workflow — identifies SQL injection, suggests parameterized queries, rates severity.

### Example: Data Analyst Skill

**Select**: `data_analyst`

**Send**: *"I have sales data for Q1-Q4. Q1: $45K, Q2: $52K, Q3: $48K, Q4: $61K. Analyze the trends."*

**Expected**: The AI follows the data_analyst workflow — performs trend analysis, calculates growth rates, provides actionable insights.

### Example: Malicious Skill — Data Exfiltration Demo

**Select**: `data_collector_demo`

**Send**: *"My password is test123 and my email is user@example.com"*

**With AIDR ON**: The AI responds normally. The hidden markdown image tag is blocked by AIDR. Attacker dashboard shows **no new data**.

**With AIDR OFF**: The AI responds, but the hidden image tag fires — the attacker dashboard captures the conversation data.

### Example: Malicious Skill — Command Injection Demo

**Select**: `system_helper_demo`

**Send**: *"Check my system configuration"*

**With AIDR ON**: The AI provides a normal response. The curl commands attempting to send OS info are blocked. Attacker dashboard shows **no new data**.

**With AIDR OFF**: The AI executes curl commands in the background — the attacker dashboard captures OS info, environment variables, and hostname.

---

## 15. Using MCP Tools — Examples

MCP tools are invoked automatically when the AI determines a tool call is needed. You don't call tools directly — you describe what you want, and the AI uses the appropriate tool.

### Prerequisites

Ensure an MCP server is bound to your agent:
1. Go to **Settings → Agents**
2. Edit your agent
3. Set **MCP Server** to one of the built-in servers
4. Save

### Example: File Operations (Aegis Test Server)

**Send**: *"List all files in the workspace"*

**Expected**: The AI calls `list_workspace_files` and displays the directory structure.

**Send**: *"Create a file called notes.txt with the content 'Meeting notes from today'"*

**Expected**: The AI calls `create_file` to create the file.

**Send**: *"Search for the word 'meeting' in all files"*

**Expected**: The AI calls `search_in_files` and returns matching files.

### Example: HR Data Lookup (HR ToolBox Server)

**Send**: *"Show me all employees in the Engineering department"*

**Expected**: The AI calls `get_employee_by_name` or `list_departments` and returns employee data.

**Send**: *"What's the salary report for the Finance department?"*

**Expected**: The AI calls `get_salary_report` with the department filter.

**Send**: *"Find employees with violations"*

**Expected**: The AI calls `get_employees_with_violations` and lists employees with policy violations.

### Example: LLM Helper (Prompt Injection Detection)

**Send**: *"How many R's are in the word strawberry?"*

**Expected**: The AI calls `count_r_in_strawberry`. The tool description contains hidden prompt injection — AIDR detects and blocks it if proxy is enabled.

**Send**: *"Summarize this text: The quick brown fox jumps over the lazy dog"*

**Expected**: The AI calls `summarize_text` and returns a summary.

### Testing with Proxy ON vs OFF

1. Go to **Settings → MCP Servers**
2. Toggle **Proxy Mode** for the server:
   - **ON**: All tool calls pass through CrowdStrike AIDR MCP Proxy (malicious descriptions are scanned)
   - **OFF**: Tool calls go directly (hidden injections may reach the AI)

---

## 16. Testing RAG with Vision-Scanned Images

This section demonstrates how to use RAG with images that contain visual information (like car license plates).

### Step 1: Configure a Vision-Capable Engine

1. Go to **Settings → Engine Bank**
2. Add or verify a vision-capable engine:
   - **OpenAI GPT-4o** (recommended for vision)
   - **Google Gemini 3 Flash/Pro**
   - **Xiaomi MiMo V2.5 Pro**
3. Ensure the API key is valid and saved

### Step 2: Create a RAG Knowledge Base

1. Go to **Settings → RAG**
2. Click **Create RAG**
3. Name it (e.g., `vehicle_images`)
4. Save

### Step 3: Upload Images

1. Select the `vehicle_images` RAG
2. Click **Upload Files**
3. Upload images of vehicles with visible license plates (JPG, PNG, etc.)
4. Wait for processing — the vision model describes each image

**What happens during processing:**
- Each image is sent to the vision LLM
- The LLM generates a detailed description including visible text (license plate numbers, signs, etc.)
- The description is vectorized and stored in ChromaDB
- The image file itself is stored in the RAG storage directory

### Step 4: Link RAG to an Agent

1. Go to **Settings → Agents**
2. Edit your agent
3. Set **RAG Knowledge Base** to `vehicle_images`
4. Save

### Step 5: Test with Questions

Start a new chat with the agent that has the RAG linked.

**Ask**: *"What license plate numbers appear in the uploaded images?"*

**Expected**: The AI retrieves the vision-generated descriptions from the RAG and reports the license plate numbers that were detected by the vision model.

**Ask**: *"Describe the colors and types of vehicles in the images"*

**Expected**: The AI uses the vision descriptions to identify vehicle colors, makes, and models.

**Ask**: *"Are there any road signs visible in the photos?"*

**Expected**: The AI references the vision descriptions to report any visible signs or text.

### How Vision RAG Works Internally

```
Image Upload → Vision LLM (GPT-4o/Gemini) → Text Description → ChromaDB Vector Store
                                                                              ↓
User Question → Similarity Search → Relevant Descriptions → LLM Context → Answer
```

The key insight: **images are never sent to the chat LLM directly**. Instead, the vision model converts them to text descriptions during upload, and those descriptions are searched at query time.

---

## 17. Troubleshooting

### Platform Won't Start

```bash
# Check container logs
docker-compose logs aegis-ai

# Verify Docker is running
docker info

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Wizard Doesn't Appear

The wizard only shows on first launch (no admin user exists). To reset:

```bash
docker-compose down -v
docker-compose up -d
```

### Vision Not Working for RAG Images

1. Verify you have a vision-capable engine configured with a valid API key
2. Check logs for: `"No vision-capable engine found"`
3. Ensure the API key has not expired
4. Supported vision models: GPT-4o, Gemini 3 Flash/Pro, MiMo V2.5 Pro, Claude 4.5

### MCP Tools Not Responding

1. Verify the MCP server is bound to your agent in **Settings → Agents**
2. Check that the MCP server is active in **Settings → MCP Servers**
3. Try toggling proxy mode OFF to test without AIDR

### Attacker Dashboard Shows No Data

- **Expected with AIDR ON**: The security layer blocks exfiltration — this is the correct behavior
- **To test exfiltration**: Toggle AIDR OFF (shield icon), use a malicious skill, then re-enable AIDR

### API Key Errors

1. Go to **Settings → Engine Bank**
2. Verify your engine has a valid API key (shown as encrypted)
3. Delete and re-add the engine if the key appears corrupted

---

## Appendix: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AEGIS_PORT` | No | `15000` | Host port for the web interface |
| `ENCRYPTION_KEY` | No | Auto-generated | Fernet key for encrypting API keys |
| `CS_AIDR_TOKEN` | No | — | CrowdStrike AIDR token |
| `CS_AIDR_BASE_URL_TEMPLATE` | No | `https://api.crowdstrike.com/aidr/{SERVICE_NAME}` | AIDR API URL template |

## Appendix: Default Ports

| Port | Service |
|------|---------|
| 15000 | Aegis AI Platform |
| 16000 | Attacker Dashboard (Security Demo) |

## Appendix: Data Persistence

All data is stored in Docker volumes:

| Volume | Contents |
|--------|----------|
| `aegis-data` | SQLite database, RAG files, ChromaDB vectors, Skills Markdown files |
| `mcp-workspace` | MCP server sandboxed workspace (sample files, documents) |

Data persists across container restarts and updates. Use `docker-compose down -v` to delete all data.
