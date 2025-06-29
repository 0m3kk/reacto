# Centralized configuration for the AI agent.

import os

# --- Main API Provider Selection ---
# Choose between 'google', 'openai', and 'openrouter'. This is the default setting.
# It can be overridden at runtime with the --api command-line argument.
API_PROVIDER = "google"

# --- Corrector API Provider Selection ---
# Choose the provider for the JSON correction model.
# Can be overridden with --corrector-api
CORRECTOR_API_PROVIDER = "google"


# --- Model Configuration ---
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# --- Gemini Configuration ---
GEMINI_REASONING_MODEL_NAME = "models/gemini-1.5-pro-latest"
GEMINI_CORRECTOR_MODEL_NAME = "models/gemini-1.5-flash-latest" # A smaller, faster model for correction

# --- OpenAI Configuration ---
OPENAI_REASONING_MODEL_NAME = "gpt-4-turbo"
OPENAI_CORRECTOR_MODEL_NAME = "gpt-3.5-turbo"

# --- OpenRouter Configuration ---
OPENROUTER_REASONING_MODEL_NAME = "google/gemini-flash-1.5"
OPENROUTER_CORRECTOR_MODEL_NAME = "google/gemini-flash-1.5" # Or another cheap, fast model


# --- API Keys ---
# It's recommended to load API keys from an environment variable for security.
# Set these in your shell:
# export GOOGLE_API_KEY='your_google_api_key'
# export OPENAI_API_KEY='your_openai_api_key'
# export OPENROUTER_API_KEY='your_openrouter_api_key'
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- Project Paths ---
# The default directory containing the user's code that the agent will work on.
# This can be overridden with the --codebase-dir command-line argument.
CODEBASE_DIR = "."

# The path where the ChromaDB vector store will be persisted.
CHROMA_DB_PATH = "chroma_db"

# --- Logging ---
# The file where the agent's thoughts, actions, and observations will be logged.
LOG_FILE = "agent.log"

# --- File Types to Index ---
# A list of file extensions to include when indexing the codebase for RAG.
SUPPORTED_FILE_TYPES = [".go", ".yaml", ".yml"]
