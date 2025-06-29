# The main entry point for the AI coding agent.

import os
import sys
import json
import logging
import difflib
import argparse
from typing import Dict, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

import config
from tools import AVAILABLE_TOOLS, search_codebase
from llm_api import get_llm_api, get_corrector_api

# --- Configuration & Setup ---
console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filename=config.LOG_FILE,
    filemode='a'
)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def get_system_prompt() -> str:
    """
    Generates the system prompt, dynamically including project rules if they exist.
    """
    rules_prompt_section = ""
    rules_file_path = os.path.join(config.CODEBASE_DIR, "RULES.MD")
    try:
        if os.path.exists(rules_file_path):
            with open(rules_file_path, 'r', encoding='utf-8') as f:
                rules_content = f.read()
            rules_prompt_section = f"""
**IMPORTANT PROJECT RULES:**
You MUST adhere to the following rules, which have been provided from the RULES.MD file in the codebase:
---
{rules_content}
---
"""
            console.print(f"[bold green]Successfully loaded rules from {rules_file_path}[/bold green]")
    except Exception as e:
        console.print(f"[bold yellow]Warning: Could not read {rules_file_path}. Error: {e}[/bold yellow]")

    return f"""
You are a sophisticated AI coding agent. Your goal is to help users with their software development tasks.

**Your Capabilities:**
You operate in a loop of Thought, Action, and Observation.
1.  **Thought:** You will reason about the user's request, break it down into steps, and decide which tool to use.
2.  **Action:** You will choose ONE tool from the available list and specify its arguments in JSON format.
3.  **Observation:** You will receive the result of your action and use it to inform your next thought.

**Your Strategy:**
- **Start with a search:** For any new task, your first step should almost always be to use the `search_codebase` tool.
- **Example:** If the user asks to "add a health check endpoint," a good first action is `search_codebase(query='examples of existing API endpoints')`.

**Project Context:**
- You are working inside the `{config.CODEBASE_DIR}` directory. All file paths and commands should be relative to this directory.
{rules_prompt_section}
**Tool Definitions:**
- `list_files(directory: str) -> str`: Lists all files and subdirectories in the specified directory.
- `read_file(filepath: str) -> str`: Reads the content of a file.
- `write_file(filepath: str, content: str) -> str`: Writes content to a file, overwriting it if it exists.
- `delete_file(filepath: str) -> str`: Deletes a file.
- `run_terminal_command(command: str) -> str`: Executes a shell command. Use for tests, linting, etc.
- `search_codebase(query: str) -> str`: Performs a semantic search on the codebase to find relevant code snippets.
- `finish(final_summary: str) -> str`: Use this tool when the task is complete to provide a summary of what you have done.

**Response Format:**
You MUST respond with a JSON object containing two keys: "thought" and "action".
The "action" MUST be another JSON object with "tool_name" and "args".

Begin!
"""

def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """Executes a tool with the given arguments and returns the result."""
    if tool_name in AVAILABLE_TOOLS:
        try:
            return AVAILABLE_TOOLS[tool_name](**args)
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"
    else:
        return f"Error: Tool '{tool_name}' not found."

def display_diff(filepath: str, new_content: str):
    """Shows a color-coded diff of the proposed changes to a file."""
    original_content = ""
    full_path = os.path.join(config.CODEBASE_DIR, filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

    diff = difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
    )

    diff_text = "".join(diff)
    if not diff_text:
        console.print(Panel("No changes detected.", title="File Write Preview", border_style="yellow"))
        return

    console.print(Panel(Syntax(diff_text, "diff", theme="monokai", line_numbers=True),
                    title=f"[bold blue]Proposed changes for {filepath}[/bold blue]",
                    border_style="blue"))


def main_loop(task: str, max_turns: int, corrector_api_provider: str):
    """The main reasoning loop of the agent."""
    try:
        llm_client = get_llm_api(config.API_PROVIDER)
        corrector_client = get_corrector_api(corrector_api_provider) if corrector_api_provider != 'none' else None
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)

    system_prompt = get_system_prompt()

    console.print("\n[bold cyan]Performing initial codebase search to get context...[/bold cyan]")
    initial_search_results = search_codebase(query=task)

    console.print(Markdown(f"**Initial Search Results:**\n---\n{initial_search_results}\n---"))

    history = [
        {"role": "user", "parts": [
            system_prompt,
            f"Here is the task: {task}\n\nTo start, I have already performed an initial search of the codebase based on your task. Here are the results:\n\n{initial_search_results}"
        ]}
    ]

    for turn in range(max_turns):
        console.print(f"\n--- Turn {turn + 1}/{max_turns} ---", style="bold yellow")

        console.print("\n[bold cyan]Generating thought and action...[/bold cyan]")

        try:
            response_text = llm_client.generate_content(history)

            # Clean the response text to be valid JSON
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            response_json = json.loads(response_text)

        except json.JSONDecodeError:
            logging.warning(f"Malformed JSON from main LLM: {response_text}")
            console.print("[bold yellow]Malformed JSON detected. Attempting to correct...[/bold yellow]")

            if not corrector_client:
                console.print("[bold red]Corrector model is disabled. Cannot fix JSON.[/bold red]")
                history.append({"role": "model", "parts": [response_text]})
                history.append({"role": "user", "parts": ["Your previous response was not valid JSON. Please correct your JSON formatting."]})
                continue

            try:
                corrected_text = corrector_client.correct_json(response_text)
                logging.info(f"Corrected JSON: {corrected_text}")
                console.print("[green]JSON corrected successfully.[/green]")
                response_text = corrected_text # Use the corrected text
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:-3].strip()
                response_json = json.loads(response_text)
            except (json.JSONDecodeError, Exception) as e:
                logging.error(f"Failed to correct JSON. Error: {e}\nOriginal: {response_text}")
                console.print("[bold red]Failed to correct JSON. Asking main model to retry.[/bold red]")
                history.append({"role": "model", "parts": [response_text]})
                history.append({"role": "user", "parts": ["Your previous response was not valid JSON, and the correction attempt failed. Please try again with valid JSON."]})
                continue

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
            break

        try:
            thought = response_json.get("thought", "No thought provided.")
            action = response_json.get("action", {})

            logging.info(f"THOUGHT: {thought}")
            console.print(Markdown(f"**Thought:** {thought}"))
        except Exception as e:
            logging.error(f"Error extracting thought/action: {e}")
            console.print(f"[bold red]Could not extract thought/action from JSON: {e}[/bold red]")
            history.append({"role": "model", "parts": [json.dumps(response_json)]})
            history.append({"role": "user", "parts": ["There was an issue processing your last valid JSON response. Please reconsider your plan."]})
            continue


        tool_name = action.get("tool_name")
        args = action.get("args", {})

        if not tool_name:
            console.print("[bold red]Error: Model did not specify a tool to use.[/bold red]")
            break

        logging.info(f"PROPOSED ACTION: {tool_name} with args {args}")
        console.print(Markdown(f"**Action:** `{tool_name}` with arguments: `{args}`"))

        if tool_name == "finish":
            console.print("\n[bold green]Task Finished![/bold green]")
            console.print(Markdown(f"**Final Summary:** {args.get('final_summary', 'No summary provided.')}"))
            break

        if tool_name == "write_file":
            display_diff(args.get("filepath", ""), args.get("content", ""))

        try:
            approval = console.input("Approve this action? (y/n): ").lower()
            if approval != 'y':
                console.print("[bold yellow]Action rejected by user. The agent will reconsider.[/bold yellow]")
                history.append({"role": "model", "parts": [json.dumps(response_json, indent=2)]})
                history.append({"role": "user", "parts": ["That action was rejected. Please think of a different approach."]})
                continue
        except KeyboardInterrupt:
            console.print("\n[bold red]Operation cancelled by user.[/bold red]")
            break

        console.print("\n[bold cyan]Executing action...[/bold cyan]")
        observation = execute_tool(tool_name, args)

        logging.info(f"OBSERVATION: {observation}")
        console.print(Markdown(f"**Observation:**\n---\n{observation}\n---"))

        history.append({"role": "model", "parts": [json.dumps(response_json, indent=2)]})
        history.append({"role": "user", "parts": [observation]})

    else:
        console.print("\n[bold red]Agent reached maximum turns. Stopping to prevent infinite loop.[/bold red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An AI agent for software development tasks.")

    parser.add_argument(
        'task',
        type=str,
        help="The high-level task for the agent to perform."
    )
    parser.add_argument(
        '--api',
        type=str,
        default=config.API_PROVIDER,
        choices=['google', 'openai', 'openrouter'],
        help=f"The API provider to use for the main reasoning model. Defaults to '{config.API_PROVIDER}'."
    )
    parser.add_argument(
        '--corrector-api',
        type=str,
        default=config.CORRECTOR_API_PROVIDER,
        choices=['google', 'openai', 'openrouter', 'none'],
        help=f"The API provider for the JSON corrector model. Use 'none' to disable. Defaults to '{config.CORRECTOR_API_PROVIDER}'."
    )
    parser.add_argument(
        '--codebase-dir',
        type=str,
        default=config.CODEBASE_DIR,
        help=f"The path to the codebase directory. Defaults to '{config.CODEBASE_DIR}'."
    )
    parser.add_argument(
        '--max-turns',
        type=int,
        default=20,
        help="The maximum number of turns the agent can take. Defaults to 20."
    )

    args = parser.parse_args()

    # --- Override config with command-line arguments ---
    config.API_PROVIDER = args.api
    config.CODEBASE_DIR = args.codebase_dir
    config.CORRECTOR_API_PROVIDER = args.corrector_api

    logging.info("--- NEW SESSION ---")
    logging.info(f"TASK: {args.task}")
    logging.info(f"API PROVIDER: {config.API_PROVIDER}")
    logging.info(f"CORRECTOR API: {config.CORRECTOR_API_PROVIDER}")
    logging.info(f"CODEBASE: {os.path.abspath(config.CODEBASE_DIR)}")
    logging.info(f"MAX TURNS: {args.max_turns}")

    console.print(f"Starting agent with task: [bold blue]'{args.task}'[/bold blue]")
    console.print(f"Working in codebase: [bold blue]'{os.path.abspath(config.CODEBASE_DIR)}'[/bold blue]")

    main_loop(task=args.task, max_turns=args.max_turns, corrector_api_provider=args.corrector_api)
