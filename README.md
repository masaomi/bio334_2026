## BIO334 Practical Bioinformatics

## The 3rd module, 20-22 May, 2026

Schedule: Wed 20 May 13:00 – Fri 22 May 12:00 (Zurich time)

Masaomi Hatakeyama
- https://github.com/masaomi/bio334_2026

## How to download/update this documents

Download
```bash
$ git clone https://github.com/masaomi/bio334_2026
```

Updating
```bash
$ git pull
```

Directories
- data/: input data used in some exercises
- examples/: source code of examples shown in the lecture
- jupyter_notebooks/: jupyter notebook files
- skeletons/: incompleted source code of exercises (you should fill in and complete it)
- simulation/: source code used in an advanced exercise of day2

## Table of Content (Plan)

**Day1** | &nbsp; 
-------|-------
13.00- | **Quick Python review** [bio334_day1_part1.ipynb](jupyter_notebooks/bio334_day1_part1.ipynb)
14.00- | **Two sequences comparison** [bio334_day1_part2.ipynb](jupyter_notebooks/bio334_day1_part2.ipynb)
15.00- | **Nucleotide diversity1** [bio334_day1_part3.ipynb](jupyter_notebooks/bio334_day1_part3.ipynb)
 &nbsp;| &nbsp;
**Day2** | &nbsp; 
9.00-12.00 | **Nucleotide diversity2**
13.00-15.00 | **Tajima's D calculation1**
15.00-17.00 | **Tajima's D calculation2**
 &nbsp;| &nbsp;
**Day3** | &nbsp; 
9.00-12.00 | **Advanced exercise**

## Google Colab

Note
* You need a google account

* [bio334_day1_part1.ipynb](https://colab.research.google.com/github/masaomi/bio334_2026/blob/main/jupyter_notebooks/bio334_day1_part1.ipynb)
* [bio334_day1_part2.ipynb](https://colab.research.google.com/github/masaomi/bio334_2026/blob/main/jupyter_notebooks/bio334_day1_part1.ipynb)

## Exercises

- Day1 Part1: https://gist.github.com/masaomi/75ac75aa49d3603697e24864b2345d4d
- Day1 Part2: https://gist.github.com/masaomi/b2f52f4723757d5fd1b93ed422f81923
- Day1 Part3: https://gist.github.com/masaomi/857f8257e4ec9d4fb80557a5890f22a3

## Recommended Python Learning Resources (2026)

### Interactive Courses & Tutorials

- **[Codecademy – Python Catalog](https://www.codecademy.com/catalog/language/python)**  
  Offers a wide range of Python courses, from beginner to advanced, covering topics like data analysis, machine learning, and web development.  ([Best Python Courses + Tutorials - Codecademy](https://www.codecademy.com/catalog/language/python?utm_source=chatgpt.com))

- **[Coursera – Python Courses](https://www.coursera.org/courses?query=python)**  
  Provides comprehensive Python courses from top universities, including the popular "Python for Everybody" by the University of Michigan.  ([Best Python Courses & Certificates [2025] | Coursera Learn Online](https://www.coursera.org/courses?query=python&utm_source=chatgpt.com))

- **[Udemy – Python Courses](https://www.udemy.com/topic/python/)**  
  Features a vast selection of Python courses, such as "100 Days of Code: The Complete Python Pro Bootcamp," suitable for learners at all levels. 

- **[LearnPython.org](https://www.learnpython.org/)**  
  A free, interactive Python tutorial for people who want to learn Python, especially suited for beginners.  ([Learn Python - Free Interactive Python Tutorial](https://www.learnpython.org/?utm_source=chatgpt.com))

- **[DataCamp – How to Learn Python](https://www.datacamp.com/blog/how-to-learn-python-expert-guide)**  
  Offers an expert guide on learning Python, including applications and the demand for Python skills.  ([How to Learn Python From Scratch in 2025: An Expert Guide](https://www.datacamp.com/blog/how-to-learn-python-expert-guide?utm_source=chatgpt.com))

- **[Mimo – 20 Best Online Resources to Learn Python](https://mimo.org/blog/how-to-learn-python-for-free-online)**  
  Lists 20 free online resources for learning Python in 2025, ranging from interactive courses to video tutorials.  ([How to Learn Python for Free: 20 Best Online Resources of 2025](https://mimo.org/blog/how-to-learn-python-for-free-online?utm_source=chatgpt.com))

### Video Tutorials

- **[Python Full Course for Beginners (2025) – YouTube](https://www.youtube.com/watch?v=K5KVEU3aaeQ)**  
  A comprehensive, beginner-friendly video course covering Python basics to advanced topics. 

### University-Level Courses

- **[CS50x – Introduction to Computer Science by Harvard](https://cs50.harvard.edu/x/)**  
  An entry-level course teaching the basics of computer science and programming, including Python.  ([CS50](https://en.wikipedia.org/wiki/CS50?utm_source=chatgpt.com))

### Practice Platforms

- **[Exercism – Python Track](https://exercism.org/tracks/python)**  
  Provides hands-on coding exercises with mentorship to help you improve your Python skills.  ([Python, AI, and robots-oh my!](https://nypost.com/2025/01/03/shopping/the-ultimate-ai-chatgpt-amp-python-programming-bundle-is-80-off/?utm_source=chatgpt.com))

---

## 🤖 AI Coding Agents (2026)

The landscape shifted decisively from *assistants* (autocomplete-style helpers) to *agents* (autonomous loops that plan, edit files, run commands, and verify results) during 2025–2026. In February 2026, almost every major tool shipped parallel multi-agent execution within the same two-week window. Below are the tools most actively used in 2026, grouped by vendor.

> ⚠️ For BIO334 students: these tools are introduced for context only. Final exams remain LLM-free, and the core exercises in this course are designed to be completed by manual typing. Use these tools after class to extend your understanding, not to bypass it.

### Anthropic — Claude

- **[Claude Code](https://www.anthropic.com/claude-code)**  
  Terminal-native coding agent from Anthropic. As of May 2026 it is widely regarded as the strongest agent for reasoning-heavy work (1M-token context, leading SWE-bench scores, hook system, MCP support, Agent Skills, sub-agents). Reportedly accounts for over half of Anthropic's enterprise revenue.
- **[Claude Desktop](https://claude.ai/download)**  
  The desktop chat client. Supports MCP servers, file uploads, and the same Claude Opus / Sonnet / Haiku 4.x model family. Useful for design discussion and document work that doesn't need direct repo access.

### OpenAI — Codex

The 2026 Codex is unrelated to the 2021 model that powered early Copilot. It is a full agent built on the `codex-1` reasoning model (descended from o3), bundled with ChatGPT subscriptions.

- **[Codex (web / ChatGPT)](https://openai.com/codex/)**  
  Cloud-sandboxed agent that clones your repo, runs servers, executes tests, and opens pull requests asynchronously. Strong for high-volume, well-scoped tasks delegated as background jobs.
- **[Codex CLI](https://github.com/openai/codex)**  
  Open-source terminal client for the same agent, comparable in shape to Claude Code. Often used alongside Claude Code (Codex for volume, Claude for depth).
- **[Codex Desktop (macOS app)](https://openai.com/codex/)**  
  Standalone desktop app launched February 2026.

### Google — Antigravity & Gemini

- **[Google Antigravity](https://antigravity.google/)**  
  Agent-first IDE released November 2025 alongside Gemini 3. A modified VS Code fork with two modes: a familiar Editor View and a Manager View that dispatches up to five parallel agents with inbox-style notifications. Defaults to a Plan → Review → Execute loop and ships an integrated Chrome instance so agents can actually open the UI they just built and screenshot the result. Supports Gemini 3.1 Pro/Flash, Claude Sonnet/Opus 4.6, and GPT-OSS-120B. Free preview with evolving credit-based pricing.
- **[Gemini Code Assist](https://cloud.google.com/products/gemini/code-assist)**  
  Google's IDE plugin (VS Code, JetBrains, Cloud Shell) and the successor to Jules. Tighter integration with Google Cloud and Workspace.
- **[Gemini CLI](https://github.com/google-gemini/gemini-cli)**  
  Open-source terminal agent powered by Gemini, with generous free-tier limits.

### Cursor

- **[Cursor](https://www.cursor.com/)**  
  VS Code fork; the dominant AI-native IDE with 1M+ users and 360K paying customers. Cursor 2.0 introduced a sub-agent system (up to 8 parallel agents), the in-house ultra-fast Composer model, and an agent-centric UI. Widely loved for UX; credit-based pricing has drawn criticism in 2026.

### GitHub Copilot

- **[GitHub Copilot](https://github.com/features/copilot)**  
  The original inline pair-programmer, now expanded with Copilot Workspace and Copilot Agents for issue-to-PR work. Strongest path when your workflow is already GitHub-native.

### Other notable agents in 2026

- **[Windsurf](https://windsurf.com/editor)** — Agentic IDE (fork of VS Code, predecessor to Antigravity's interaction model); flat $15/month, popular as a Cursor alternative.
- **[Kiro](https://kiro.dev/)** — Spec-driven coding agent; emphasizes writing executable specifications before code.
- **[Devin](https://devin.ai/)** — Cognition's autonomous software engineer; parallel sessions, runs as a long-lived background agent.
- **[Cline](https://cline.bot/)** — Open-source VS Code extension with Plan/Act modes; bring-your-own-key, model-agnostic.
- **[Augment / Auggie](https://www.augmentcode.com/)** — Strong scaffolding around frontier models; notably outperformed Claude Code on SWE-bench Verified using the same underlying model, illustrating that **agent architecture matters as much as the model**.
- **[Grok Build](https://x.ai/)** — xAI's coding agent, ships with 8 parallel agents.

### How to think about the field

Same model, different scaffolding, different results. The choice between these tools is less about "which model is smartest" and more about **which control surface fits your workflow** — terminal (Claude Code, Codex CLI, Gemini CLI), IDE (Cursor, Antigravity, Windsurf), cloud-async (Codex web, Devin), or GitHub-native (Copilot). For learning Python and population genetics from scratch, the right answer in 2026 is still: write the code yourself first, understand every line, *then* learn to direct an agent. The agents will be here next year; the conceptual foundation you build now is what makes you able to evaluate what they produce.

Sources for this section:
- [The Best AI Coding Tools of May 2026 — Medium](https://medium.com/@chaos.architect25/the-best-ai-coding-tools-of-may-2026-cf2db2804a0f)
- [AI Coding Agents 2026 Comparison — Lushbinary](https://lushbinary.com/blog/ai-coding-agents-comparison-cursor-windsurf-claude-copilot-kiro-2026/)
- [Every AI Coding CLI in 2026 — DEV Community](https://dev.to/soulentheo/every-ai-coding-cli-in-2026-the-complete-map-30-tools-compared-4gob)
- [Coding Agents Comparison — Artificial Analysis](https://artificialanalysis.ai/agents/coding)
- [Google Antigravity — Wikipedia](https://en.wikipedia.org/wiki/Google_Antigravity)
- [Build with Google Antigravity — Google Developers Blog](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)

