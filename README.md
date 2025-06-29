# 🤖 Reacto: Your AI Coding Partner

Reacto is a sophisticated, interactive AI assistant designed to streamline complex software development tasks. It goes beyond a simple chatbot by reasoning about your codebase, planning multi-step actions, and executing them with your explicit approval.

-----

### ✨ Features

  * **🧠 Advanced Reasoning:** Powered by high-end models like **Google's Gemini 1.5 Pro** and **OpenAI's GPT-4 Turbo**. It uses the ReAct (Reason-Act) framework to break down complex problems.
  * **📚 Codebase-Aware:** Leverages a Retrieval-Augmented Generation (RAG) system with **ChromaDB** to understand the specific context of your project's code.
  * **🛡️ Safety First (Human-in-the-Loop):** **No action is ever taken automatically.** Every proposed command, from writing a file to running a test, requires your explicit `y/n` approval.
  * **👀 Diff-based Review:** Before writing to a file, the agent shows you a clear, color-coded `diff` of the proposed changes, so you know exactly what you're approving.
  * **🔌 Multi-API Support:** Natively supports `Google Gemini`, `OpenAI`, and `OpenRouter`, allowing you to choose the best model for your needs and budget.
  * **🤖 Self-Correcting JSON:** Automatically uses a smaller, faster model to fix formatting errors from the main model, reducing interruptions.
  * **⚙️ Extensible Toolset:** Comes with essential tools for file system management, terminal command execution, and semantic code search.
  * **📜 Project-Specific Rules:** Automatically ingests and adheres to guidelines defined in a `RULES.MD` file in your project's root.

-----

### 🚀 Getting Started

#### 1\. Prerequisites

  * Python 3.8+
  * An API key from Google, OpenAI, or OpenRouter.

#### 2\. Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/0m3kk/reacto.git
    cd reacto
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up API Keys:**
    Create a `.env` file in the project root or set environment variables. The agent will automatically load them.

    ```bash
    # For Google
    GOOGLE_API_KEY="your_google_api_key"

    # For OpenAI
    OPENAI_API_KEY="your_openai_api_key"

    # For OpenRouter
    OPENROUTER_API_KEY="your_openrouter_api_key"
    ```

#### 3\. Index Your Codebase

Before you can use the agent, you need to create a searchable vector index of your project.

1.  Place your project's code into the `your_project_to_work_on` directory (or specify a different directory with the `--codebase-dir` flag).

2.  Run the setup script:

    ```bash
    python setup_codebase.py --codebase-dir /path/to/your/project
    ```

    This only needs to be done once, or whenever your codebase has significant changes.

-----

### 💻 Usage

Run the agent from your terminal by providing a high-level task.

#### Basic Command

```bash
python agent.py "Refactor the user authentication logic in auth.go to be more modular."
```

#### Command-Line Arguments

  * `task` (Required): The task you want the agent to perform, enclosed in quotes.
  * `--api`: Choose the API provider.
      * `google` (default), `openai`, `openrouter`
  * `--corrector-api`: Choose the provider for the JSON correction model.
      * `google` (default), `openai`, `openrouter`, `none` (to disable)
  * `--codebase-dir`: Path to the codebase the agent should work on.
      * Defaults to `your_project_to_work_on`.
  * `--max-turns`: The maximum number of thought-action-observation cycles.
      * Defaults to `20`.

#### Example with Flags

This command runs the agent on a Go project using OpenRouter for the main model and Gemini for correction.

```bash
python agent.py "Implement a new GraphQL endpoint for user profiles" --api openrouter --corrector-api google --codebase-dir ./my-go-app
```
