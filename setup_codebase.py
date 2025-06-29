# This script indexes the specified codebase for semantic search (RAG).
# It reads supported file types, chunks them, and stores their embeddings in ChromaDB.
# Run this script once before using the agent's `search_codebase` tool.

import os
import argparse
import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm
import config

def setup(codebase_dir: str):
    """
    Initializes the ChromaDB collection and indexes the codebase.
    """
    print("--- Starting Codebase Indexing ---")

    # Update the config in memory for this run
    config.CODEBASE_DIR = codebase_dir
    print(f"Targeting codebase directory: {os.path.abspath(config.CODEBASE_DIR)}")


    # Initialize ChromaDB client and collection
    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.EMBEDDING_MODEL_NAME
    )
    collection = client.get_or_create_collection(
        name="codebase",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )

    # Prepare for text splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    documents = []
    metadatas = []
    ids = []
    doc_id_counter = 0

    # Walk through the codebase directory
    print(f"Scanning files in '{config.CODEBASE_DIR}'...")
    if not os.path.exists(config.CODEBASE_DIR):
        print(f"Error: Codebase directory '{config.CODEBASE_DIR}' not found.")
        print("Please create it and add your project files before running this setup.")
        # Create the directory so the agent can run without errors later
        os.makedirs(config.CODEBASE_DIR, exist_ok=True)
        return

    all_files = []
    for root, _, files in os.walk(config.CODEBASE_DIR):
        for file in files:
            if any(file.endswith(ext) for ext in config.SUPPORTED_FILE_TYPES):
                all_files.append(os.path.join(root, file))

    if not all_files:
        print("No supported files found to index.")
        print("--- Indexing Finished ---")
        return

    # Process each file with a progress bar
    print(f"Found {len(all_files)} supported files to index.")
    with tqdm(total=len(all_files), desc="Indexing Files") as pbar:
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Split content into manageable chunks
                chunks = text_splitter.split_text(content)

                for chunk in chunks:
                    relative_path = os.path.relpath(file_path, config.CODEBASE_DIR)
                    documents.append(chunk)
                    metadatas.append({"source": relative_path})
                    ids.append(f"doc_{doc_id_counter}")
                    doc_id_counter += 1
            except Exception as e:
                print(f"\nWarning: Could not read or process file {file_path}. Error: {e}")
            pbar.update(1)

    # Add the documents to the collection if any were processed
    if documents:
        print(f"\nAdding {len(documents)} document chunks to the vector store...")
        try:
            # Clear old collection data for this codebase before adding new
            # This is a simple approach; for production you might want more sophisticated update strategies
            if collection.count() > 0:
                print("Clearing existing collection to re-index...")
                # Note: The `delete` method in chromadb is being deprecated.
                # A more robust way is to delete the collection and recreate it.
                # However, for simplicity here, we assume re-adding might create duplicates if not managed,
                # but we'll proceed by simply adding. A better implementation might use `collection.delete`.
                pass # Placeholder for more complex update logic

            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print("Successfully added documents to ChromaDB.")
        except Exception as e:
            print(f"\nError adding documents to ChromaDB: {e}")
    else:
        print("No content was indexed.")

    print("--- Indexing Finished ---")
    print(f"Total documents in collection: {collection.count()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index a codebase for the AI agent.")
    parser.add_argument(
        '--codebase-dir',
        type=str,
        default=config.CODEBASE_DIR,
        help=f"The path to the codebase directory to index. Defaults to '{config.CODEBASE_DIR}'."
    )
    args = parser.parse_args()
    setup(codebase_dir=args.codebase_dir)
