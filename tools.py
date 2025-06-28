import os
import subprocess
import chromadb
from chromadb.utils import embedding_functions
import config

# --- Initialize ChromaDB for Codebase Search ---
# This setup allows the agent to perform semantic searches on the indexed codebase.

# Use a local sentence-transformer model for embeddings. This runs on your machine and is free.
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=config.EMBEDDING_MODEL_NAME
)

# Initialize the ChromaDB client with the persistent storage path.
client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)

# Get or create the collection for the codebase.
collection = client.get_or_create_collection(
    name="codebase",
    embedding_function=embedding_function,
    metadata={"hnsw:space": "cosine"} # Using cosine distance for semantic similarity
)

# --- Tool Definitions ---

def list_files(directory: str = '.') -> str:
    """
    Lists all files and directories within a specified directory in the codebase.
    The path is relative to the project's root directory.
    """
    try:
        # Security check: Ensure the path is within the allowed codebase directory
        base_path = os.path.abspath(config.CODEBASE_DIR)
        target_path = os.path.abspath(os.path.join(base_path, directory))
        if not target_path.startswith(base_path):
            return "Error: Access denied. Path is outside the codebase directory."

        if not os.path.exists(target_path):
            return f"Error: Directory '{directory}' not found."

        files = os.listdir(target_path)
        return "\n".join(files) if files else "The directory is empty."
    except Exception as e:
        return f"Error listing files: {e}"

def read_file(filepath: str) -> str:
    """
    Reads the entire content of a specified file.
    The path is relative to the project's root directory.
    """
    try:
        # Security check
        full_path = os.path.join(config.CODEBASE_DIR, filepath)
        if not os.path.abspath(full_path).startswith(os.path.abspath(config.CODEBASE_DIR)):
             return "Error: Access denied. Path is outside the codebase directory."

        if not os.path.exists(full_path):
            return f"Error: File '{filepath}' not found."

        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(filepath: str, content: str) -> str:
    """
    Writes content to a specified file. Creates the file if it doesn't exist.
    Overwrites the file if it already exists.
    The path is relative to the project's root directory.
    """
    try:
        # Security check
        full_path = os.path.join(config.CODEBASE_DIR, filepath)
        if not os.path.abspath(full_path).startswith(os.path.abspath(config.CODEBASE_DIR)):
             return "Error: Access denied. Path is outside the codebase directory."

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File '{filepath}' has been written successfully."
    except Exception as e:
        return f"Error writing file: {e}"

def delete_file(filepath: str) -> str:
    """
    Deletes a specified file.
    The path is relative to the project's root directory.
    """
    try:
        # Security check
        full_path = os.path.join(config.CODEBASE_DIR, filepath)
        if not os.path.abspath(full_path).startswith(os.path.abspath(config.CODEBASE_DIR)):
             return "Error: Access denied. Path is outside the codebase directory."

        if not os.path.exists(full_path):
            return f"Error: File '{filepath}' not found."

        os.remove(full_path)
        return f"File '{filepath}' has been deleted successfully."
    except Exception as e:
        return f"Error deleting file: {e}"

def run_terminal_command(command: str) -> str:
    """
    Executes a shell command in the terminal.
    IMPORTANT: This is a powerful tool. For safety, it runs within the codebase directory.
    Only use it for development tasks like running tests, linters, or installing dependencies.
    """
    try:
        # Security: Run the command within the specified codebase directory
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=config.CODEBASE_DIR,
            timeout=120 # Add a timeout to prevent hanging processes
        )
        output = f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}"
        return output
    except FileNotFoundError:
        return "Error: Command not found. Make sure the tool is installed and in your PATH."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {e}"

def search_codebase(query: str, n_results: int = 5) -> str:
    """
    Performs a semantic search over the indexed codebase using a search query.
    Returns the top `n_results` most relevant code snippets.
    Useful for finding examples, relevant functions, or understanding existing patterns.
    """
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        if not results or not results['documents'][0]:
            return "No relevant code snippets found in the codebase."

        # Format the results for clarity
        output = "Found the following relevant code snippets:\n\n"
        for i, doc in enumerate(results['documents'][0]):
            output += f"--- Snippet {i+1} (from file: {results['metadatas'][0][i]['source']}) ---\n"
            output += f"{doc}\n\n"
        return output
    except Exception as e:
        return f"Error searching codebase: {e}"

# --- Tool Mapping ---
# A dictionary to easily access the tools by name.
AVAILABLE_TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file,
    "run_terminal_command": run_terminal_command,
    "search_codebase": search_codebase,
}
