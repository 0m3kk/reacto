# Centralized configuration for the AI agent.

import os

# --- Model Configuration ---
# You can choose to use a local model for embeddings or an API-based one.
# For local embeddings, 'sentence-transformers/all-MiniLM-L6-v2' is a good starting point.
# For API-based, you might use 'models/embedding-001'.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# The main reasoning model.
REASONING_MODEL_NAME = "models/gemini-2.5-flash"

# --- API Keys ---
# It's recommended to load the API key from an environment variable for security.
# Set this in your shell: export GOOGLE_API_KEY='your_api_key_here'
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Project Paths ---
# The directory containing the user's code that the agent will work on.
# IMPORTANT: The agent will have read/write/execute permissions in this directory.
CODEBASE_DIR = "/Users/nhatpm/Projects/eventus"

# The path where the ChromaDB vector store will be persisted.
CHROMA_DB_PATH = "chroma_db"

# --- Logging ---
# The file where the agent's thoughts, actions, and observations will be logged.
LOG_FILE = "agent.log"

# --- File Types to Index ---
# A list of file extensions to include when indexing the codebase for RAG.
SUPPORTED_FILE_TYPES = [".go", ".yaml", ".yml"]
