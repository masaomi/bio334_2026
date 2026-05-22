# BIO334 Teaching Chain

An AI-powered teaching assistant for **BIO334 Practical Bioinformatics** at the University of Zurich. Students learn Python programming through population genetics problems, culminating in the analysis of *Arabidopsis kamchatica* homoeolog nucleotide diversity.

## Overview

The Teaching Chain guides students through a 3-day intensive module using a four-layer pedagogical model:

1. **Conceptual Understanding** — Explain what is being computed and why
2. **Instruction** — Give precise instructions to AI
3. **Implementation Literacy** — Read and verify AI-generated code
4. **Result Verification** — Interpret results biologically

Three interfaces are available:

| Interface | Description | API Key Required |
|-----------|-------------|-----------------|
| **Web GUI** | Browser-based IDE with chat, code editor, and progress tracking | Yes |
| **MCP Server** | Integrates with Claude Code / Claude Desktop as a teaching tool | No (uses host LLM) |
| **CLI** | Command-line launcher for both modes | Depends on mode |

## Requirements

- **Python 3.10+**
- **Anthropic API key** (for Web GUI mode)
- **Claude Code** (for MCP mode, optional)

## Quick Start

There are two ways to use the Teaching Chain. Choose the one that fits your setup:

| Path | What you need | Best for |
|------|--------------|----------|
| **A. Web GUI** | Anthropic API key | Classroom use, self-study with browser UI |
| **B. Claude Code + MCP** | Claude Code (Pro/Max plan) | Developers, terminal-based workflow |

### 1. Extract and Install

```bash
# Extract the archive
tar xzf bio334-teaching.tar.gz
cd bio334-teaching

# Install the package and its dependencies
pip install -e .

# For MCP server support (Path B), also install:
pip install -e ".[mcp]"
```

This installs FastAPI, uvicorn, the Anthropic SDK, and creates the `bio334-teaching` command.

---

### Path A: Web GUI (requires API key)

#### A-1. Get an Anthropic API Key

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to **API Keys** and create a new key
4. Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or pass it directly when launching:

```bash
bio334-teaching serve --api-key "sk-ant-..."
```

#### A-2. Launch the Web GUI

```bash
bio334-teaching serve
```

This starts a local web server at `http://127.0.0.1:8334` and opens your browser automatically.

**Options:**

```bash
bio334-teaching serve --port 9000          # Custom port
bio334-teaching serve --no-browser         # Don't auto-open browser
bio334-teaching serve --backend api        # Force Anthropic API backend
bio334-teaching serve --backend claude-code # Use local Claude Code as backend (no API key needed)
```

#### A-3. Using the Web GUI

1. **Enter your name** in the onboarding screen
2. **Chat** with the teaching assistant in the left panel
3. **Write code** in the editor (right panel) and click **Run** to execute
4. Use **Args** field next to Run for command-line arguments (e.g., filenames for `sys.argv`)
5. **Save** your session at any time (creates a labeled save point)
6. **Resume** a previous session to restore chat history
7. **Export** chat logs or summaries per save point
8. **Progress** button shows your learning progress across all topics

---

### Path B: Claude Code + MCP (no API key needed)

If you have [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (requires a Claude Pro or Max subscription), you can use the Teaching Chain without an Anthropic API key. Claude Code itself acts as the teaching LLM.

#### B-1. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

#### B-2. Configure MCP

Create a `.mcp.json` file in the directory where you will work:

```json
{
  "mcpServers": {
    "bio334-teaching": {
      "command": "bio334-teaching",
      "args": ["mcp"]
    }
  }
}
```

#### B-3. Start Learning

```bash
claude
```

Claude will automatically connect to the Teaching Chain MCP server. You can ask it to teach you BIO334 topics, and it will use the full knowledge base, track your progress, and run your Python code.

## Additional MCP Configuration

### Claude Desktop

You can also use the MCP server with Claude Desktop. Add to your configuration file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bio334-teaching": {
      "command": "bio334-teaching",
      "args": ["mcp"]
    }
  }
}
```

### MCP over HTTP (alternative)

```bash
bio334-teaching mcp --http --port 8335
```

## Project Structure

```
bio334-teaching/
├── pyproject.toml                 # Package configuration
├── README.md                      # This file
└── src/bio334_teaching/
    ├── cli.py                     # CLI entry point
    ├── core/                      # Core logic
    │   ├── chat.py                # Chat engine (topic detection, progress tracking)
    │   ├── knowledge.py           # Knowledge base loader
    │   ├── progress.py            # Student progress (4-layer tracking)
    │   ├── prompt.py              # System prompt builder
    │   ├── sandbox.py             # Python code execution sandbox
    │   └── timetable.py           # Schedule-aware teaching
    ├── interfaces/
    │   ├── web/                   # FastAPI web application
    │   └── mcp/                   # MCP server (stdio + HTTP)
    ├── knowledge/                 # 13 teaching knowledge files (Markdown)
    │   ├── system_prompt.md       # AI teaching persona
    │   ├── popgen_*.md            # Population genetics topics
    │   ├── python_*.md            # Python programming topics
    │   ├── akamchatica_biology.md # Biological context
    │   └── summaries/             # Compressed summaries for token budget
    ├── data/examples/             # Example FASTA/VCF files for exercises
    ├── static/                    # Web GUI (HTML/CSS/JS)
    └── workspace/                 # Student code workspace (created at runtime)
```

## Course Content

The teaching knowledge covers:

**Population Genetics**: nucleotide diversity (pi), segregating sites, Watterson's theta, Tajima's D, Wright-Fisher simulation, net divergence (D_a)

**Python Programming**: basics, file I/O (FASTA/VCF parsing), functions and modules, batch processing

**Biology**: *A. kamchatica* allotetraploid biology, HMA4 gene, homoeolog analysis

**Example Data**: FASTA and VCF files for *A. kamchatica* halleri/lyrata homoeologs, with expected output values for verification

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required for Web GUI) |
| `BIO334_PROGRESS_DIR` | Custom directory for student progress files (default: `~/.bio334/`) |

### Backend Selection

The Web GUI supports two chat backends:

- **`api`** (default): Uses the Anthropic API directly. Requires `ANTHROPIC_API_KEY`.
- **`claude-code`**: Uses a local Claude Code installation as the backend. Requires Claude Code to be installed (`npm install -g @anthropic-ai/claude-code`).
- **`auto`**: Tries `api` first, falls back to `claude-code`.

## Troubleshooting

**"No API key" error in Web GUI:**
Set `ANTHROPIC_API_KEY` as an environment variable or pass `--api-key` on the command line.

**Port already in use:**
The server automatically finds the next available port. You can also specify a custom port with `--port`.

**MCP server not detected in Claude Code:**
Ensure `bio334-teaching` is installed and accessible in your PATH. Test with: `bio334-teaching version`

**Code execution not working:**
The sandbox executes Python in a subprocess. Ensure `python3` is available in your PATH.

## Notes for Instructors

### API Key Distribution for Classroom Use

For courses or workshops using the Web GUI (Path A), the instructor can distribute time-limited API keys to students instead of requiring each student to create their own Anthropic account:

1. **Create a dedicated API key** on [console.anthropic.com](https://console.anthropic.com/) under your organization's workspace
2. **Set spending limits** and expiration dates per key (Settings → Limits)
3. **Distribute the key** to students at the start of the course (e.g., via a shared document or environment setup script)
4. **Revoke the key** after the course ends

This allows students to start learning immediately without account setup overhead. A single API key can be shared among students (usage is metered, not concurrent-session-limited), or you can create one key per student for finer-grained cost tracking.

**Cost estimate**: A typical 3-day BIO334 session uses approximately $5–15 in API credits per student, depending on usage intensity.

### Alternative: No API Key Needed

If students have access to **Claude Pro or Max subscriptions** (which include Claude Code), they can use Path B (MCP mode) with no API key at all. This is ideal for:
- Students who already have Claude subscriptions
- Self-study outside of scheduled course time
- Situations where API key distribution is impractical

### Customizing the Course

The teaching knowledge files in `src/bio334_teaching/knowledge/` are plain Markdown and can be edited to adapt the course for different organisms, datasets, or learning objectives. The system prompt (`system_prompt.md`) controls the AI teaching persona's behavior.

## License

MIT

## Author

Dr. Masaomi Hatakeyama — University of Zurich / Functional Genomics Center Zurich
