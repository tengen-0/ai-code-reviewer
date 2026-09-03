# AI-Powered Code Reviewer 🤖🔍

An enterprise-grade, multi-model automated code review system built for modern software engineering teams. It leverages advanced LLMs to analyze pull requests, detect security vulnerabilities, ensure code style adherence, and provide actionable architectural feedback.

## 🚀 Key Features

- **Automated PR Analysis**: Integrates directly with GitHub Actions and Webhooks to review pull requests instantly upon opening or updating.
- **Security Vulnerability Scanning**: Detects OWASP Top 10 vulnerabilities, hardcoded secrets, and unsafe dependency usage.
- **Architectural Compliance**: Evaluates code changes against defined design patterns and domain boundaries.
- **Customizable Rulesets**: Easily configure custom review prompts and strictness levels for different repositories.

## 🛠️ Tech Stack

- **Core**: Python 3.11, FastAPI, Pydantic v2
- **LLM Integration**: OpenAI, Anthropic, and local open-source models via unified abstraction
- **CI/CD**: GitHub Actions, Docker
- **Testing**: Pytest, Ruff for linting

## 📦 Getting Started

### Prerequisites

- Python 3.11+
- Poetry or pip
- GitHub Personal Access Token

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/tengen-0/ai-code-reviewer.git
   cd ai-code-reviewer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. Run the service:
   ```bash
   uvicorn main:app --reload
   ```

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
