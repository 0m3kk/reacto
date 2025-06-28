# The main entry point for the AI coding agent.

import sys
import json
import logging
from typing import Dict, Any

import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown

import config
from tools import AVAILABLE_TOOLS

# --- Configuration & Setup ---
console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filename=config.LOG_FILE,
    filemode='a'
)
# Add a stream handler to also print logs to the console
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

# Configure the Gemini API
if not config.GOOGLE_API_KEY:
    console.print("[bold red]Error: GOOGLE_API_KEY environment variable not set.[/bold red]")
    sys.exit(1)

genai.configure(api_key=config.GOOGLE_API_KEY)
model = genai.GenerativeModel(config.REASONING_MODEL_NAME)


# --- System Prompt ---
# This prompt defines the agent's persona, capabilities, and constraints.
SYSTEM_PROMPT = f"""
You are a sophisticated AI coding agent. Your goal is to help users with their software development tasks.

**Your Capabilities:**
You operate in a loop of Thought, Action, and Observation.
1.  **Thought:** You will reason about the user's request, break it down into steps, and decide which tool to use.
2.  **Action:** You will choose ONE tool from the available list and specify its arguments in JSON format.
3.  **Observation:** You will receive the result of your action and use it to inform your next thought.

**Project Context:**
- You are working inside the `{config.CODEBASE_DIR}` directory. All file paths and commands should be relative to this directory.
- Before making any changes, you should always explore the codebase first using `list_files` and `read_file` to understand the context.

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

Example Response:
```json
{{
    "thought": "I need to see what files are in the root directory to start.",
    "action": {{
        "tool_name": "list_files",
        "args": {{
            "directory": "."
        }}
    }}
}}
```

When the task is fully complete, use the `finish` tool.
```json
{{
    "thought": "I have successfully refactored the function and verified the tests pass. The task is complete.",
    "action": {{
        "tool_name": "finish",
        "args": {{
            "final_summary": "The main function was refactored into three smaller, more manageable functions. All existing tests continue to pass."
        }}
    }}
}}
```

Begin!
"""

def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """Executes a tool with the given arguments and returns the result."""
    if tool_name in AVAILABLE_TOOLS:
        try:
            # Pass arguments to the tool function
            return AVAILABLE_TOOLS[tool_name](**args)
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"
    else:
        return f"Error: Tool '{tool_name}' not found."

def main_loop(initial_task: str):
    """The main reasoning loop of the agent."""
    history = [
        {"role": "user", "parts": [SYSTEM_PROMPT, f"Here is the task: {initial_task}"]}
    ]
    max_turns = 20  # Safety brake to prevent infinite loops

    for turn in range(max_turns):
        console.print(f"\n--- Turn {turn + 1} ---", style="bold yellow")

        # --- 1. THINK ---
        console.print("\n[bold cyan]Generating thought and action...[/bold cyan]")

        try:
            # Generate the agent's response
            response = model.generate_content(history)
            response_text = response.text

            # Clean the response text to be valid JSON
            # Models sometimes output markdown ```json ... ```, so we strip it.
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            response_json = json.loads(response_text)
            thought = response_json.get("thought", "No thought provided.")
            action = response_json.get("action", {})

            # Log and display the thought process
            logging.info(f"THOUGHT: {thought}")
            console.print(Markdown(f"**Thought:** {thought}"))

        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logging.error(f"Error parsing model response: {e}\nRaw response: {response.text}")
            console.print("[bold red]Error: Could not parse the model's response. Trying again.[/bold red]")
            history.append({"role": "model", "parts": [response.text]})
            history.append({"role": "user", "parts": ["Please correct your JSON formatting and provide a valid thought and action."]})
            continue
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
            break


        # --- 2. ACT ---
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

        # --- HUMAN-IN-THE-LOOP APPROVAL ---
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

        # --- 3. OBSERVE ---
        console.print("\n[bold cyan]Executing action...[/bold cyan]")
        observation = execute_tool(tool_name, args)

        # Log and display the observation
        logging.info(f"OBSERVATION: {observation}")
        console.print(Markdown(f"**Observation:**\n---\n{observation}\n---"))

        # Update history
        history.append({"role": "model", "parts": [json.dumps(response_json, indent=2)]})
        history.append({"role": "user", "parts": [observation]})

    else:
        console.print("\n[bold red]Agent reached maximum turns. Stopping to prevent infinite loop.[/bold red]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[bold red]Usage: python agent.py \"<your task>\"[/bold red]")
    else:
        task = " ".join(sys.argv[1:])
        logging.info("--- NEW SESSION ---")
        logging.info(f"INITIAL TASK: {task}")
        console.print(f"Starting agent with task: [bold blue]'{task}'[/bold blue]")
        main_loop(initial_task=task)
