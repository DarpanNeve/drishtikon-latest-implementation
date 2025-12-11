# reading/rag.py
import time
import os
import tempfile
import uuid
from google import genai 
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# We use a constant display name for persistence across runs.
STORE_DISPLAY_NAME = "reading-store-display" 

def _get_or_create_file_search_store(client: genai.Client) -> str:
    """
    Checks for an existing store by display name. If found, returns its resource name.
    If not found, creates a new one and returns its resource name.
    Raises ClientError on permission failure (403).
    """
    print(f"Checking for existing store with display name: '{STORE_DISPLAY_NAME}'...")

    # 1. SEARCH FOR EXISTING STORE BY DISPLAY NAME
    try:
        # Note: client.file_search_stores.list() returns an iterator
        for store in client.file_search_stores.list():
            if store.display_name == STORE_DISPLAY_NAME:
                print(f"✅ Found existing store: {store.name}")
                return store.name
    except ClientError as e:
        # This handles the 403 PERMISSION_DENIED error during the list attempt.
        print("\n❌ CRITICAL PERMISSION ERROR DURING STORE LISTING/ACCESS ❌")
        print("Your API key lacks permissions to list File Search Stores. Error details below.")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred during store listing: {e}")
        raise e

    # 2. CREATE NEW STORE (if not found)
    print("Store not found. Attempting to create a new one...")
    try:
        # Use the successful documentation pattern: name is auto-generated
        file_search_store = client.file_search_stores.create(
            config={'display_name': STORE_DISPLAY_NAME}
        )
        print(f"✅ Created new store: {file_search_store.name}")
        return file_search_store.name
    except ClientError as e:
        # This catches errors like ALREADY_EXISTS (if two processes try to create simultaneously) 
        # or another 403 on the create step.
        if 'ALREADY_EXISTS' in str(e):
             # Recursively call to retrieve the store that was just created by another process
             return _get_or_create_file_search_store(client)
        
        print("\n❌ CRITICAL ERROR DURING STORE CREATION ❌")
        raise e


def upload_text_to_store(text: str) -> str | None:
    """
    Manages the RAG lifecycle: gets/creates store, uploads text, and indexes.
    Returns the full resource name of the store used.
    """
    client = genai.Client()
    store_name = None

    try:
        # 1. Get or Create the File Search Store
        store_name = _get_or_create_file_search_store(client)
        if not store_name:
            # Should not happen if _get_or_create raises errors correctly, but as a safeguard.
            return None 

        # 2. Create temporary file
        # Use mode="w" (write) and encoding="utf-8" for proper text handling
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".txt") as f:
            f.write(text)
            file_path = f.name
        print(f"Created temp file: {file_path}")

        # 3. Upload + index file
        # Use a unique display name for the file to prevent conflicts in the store
        file_display_name = f"reading-doc-{uuid.uuid4().hex[:8]}"

        print(f"Uploading and indexing file to store {store_name}...")
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
            config={
                'display_name': file_display_name
            }
        )
        
        # Wait for the indexing operation to complete
        while not operation.done:
            time.sleep(1)
            operation = client.operations.get(operation) 
            print(".", end="", flush=True)

        print("\n✅ Upload and indexing complete.")
        os.remove(file_path)
        return store_name
    
    except Exception as e:
        print(f"\n--- FATAL UPLOAD ERROR ---")
        print(e)
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path) # Clean up temp file on failure
        return None

def rag_query(question: str, store_name: str) -> str:
    """
    Runs a RAG query against the specified File Search store.
    """
    client = genai.Client()

    # --- CRITICAL FIX: Extract the simple ID for the tool configuration ---
    # The tool configuration requires only the part after the slash.
    
    simple_store_name = store_name 
    
    tool_store_names = [simple_store_name]
    # ---------------------------------------------------------------------

    try:
        print(f"Querying store {store_name} using tool name: {simple_store_name} with question: '{question}'")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=question,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            # Pass the corrected, simple name format
                            file_search_store_names=tool_store_names
                        )
                    )
                ]
            )
        )
        
        # --- ROBUST CITATION CHECK ---
        citations = []
        if (response.candidates and 
            response.candidates[0].grounding_metadata and
            response.candidates[0].grounding_metadata.grounding_chunks):
            
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                uri = chunk.retrieved_context.uri
                # Safely split the URI, handling cases where it might be None or empty
                if uri:
                    file_name = uri.split('/')[-1]
                    citations.append(f" - Source: {file_name}")
                else:
                    citations.append(" - Source: [Unknown File]")
            
            citations_text = '\n'.join(citations)
            
            return (f"**Answer:** {response.text.strip()}\n\n"
                    f"**Grounding Citations:**\n{citations_text}")
        
        # If no grounding metadata is found
        return f"**Answer:** {response.text.strip()} (No specific grounding information found)."

    except Exception as e:
        return f"RAG Query Error: {e}"
if __name__ == "__main__":
    # Example to test the rag_query function independently
    client = genai.Client()
    
    # 1. Get the store name using the helper (This ensures the store exists)
    try:
        store_name = _get_or_create_file_search_store(client)
    except Exception as e:
        print(f"Could not initialize RAG testing due to error: {e}")
        exit()

    print("\nStarting RAG Query Test Loop...")
    while True:
        question = input("Ask a question (or hit Enter to quit): ")
        if not question.strip():
            break
        print("=========== RAG ANSWER ==========")
        # Note: When running __main__, we assume the store has content already
        answer = rag_query(question, store_name)
        print(answer)
        print("=================================\n")

    # Optional cleanup (comment out if you want to keep the store)
    # try:
    #     print(f"Cleaning up store: {store_name}...")
    #     client.file_search_stores.delete(name=store_name, config={'force': True})
    #     print("Cleanup successful.")
    # except Exception:
    #     print("Warning: Could not delete store.")