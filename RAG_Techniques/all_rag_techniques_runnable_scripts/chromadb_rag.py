import os
import sys
import argparse
import time
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from a .env file (e.g., OpenAI API key)
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "mock_key_for_testing"

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helper_functions import *
from evaluation.evalute_rag import *


class ChromaDBRAG:
    """
    A class to handle the ChromaDB RAG process for document chunking, collection indexing, and query retrieval.
    """

    def __init__(self, path, chunk_size=1000, chunk_overlap=200, n_retrieved=2, persist_directory=None, collection_name="rag_chroma"):
        """
        Initializes ChromaDBRAG by encoding the document into a Chroma vector store and creating the retriever.

        Args:
            path (str): Path to the PDF file to encode.
            chunk_size (int): Size of each text chunk (default: 1000).
            chunk_overlap (int): Overlap between consecutive chunks (default: 200).
            n_retrieved (int): Number of chunks to retrieve for each query (default: 2).
            persist_directory (str): Directory for persistent Chroma DB storage (default: None for in-memory).
            collection_name (str): Collection name for Chroma DB.
        """
        print("\n--- Initializing ChromaDB RAG Retriever ---")

        # Encode the PDF document into a Chroma vector store using OpenAI embeddings
        start_time = time.time()
        self.vector_store = encode_pdf(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            vectorstore_type="chroma",
            persist_directory=persist_directory,
            collection_name=collection_name
        )
        self.time_records = {'Chunking': time.time() - start_time}
        print(f"Chunking & Indexing Time: {self.time_records['Chunking']:.2f} seconds")

        # Create a retriever from the Chroma vector store
        self.chunks_query_retriever = self.vector_store.as_retriever(search_kwargs={"k": n_retrieved})

    def run(self, query):
        """
        Retrieves and displays the context for the given query using ChromaDB.

        Args:
            query (str): The query to retrieve context for.

        Returns:
            tuple: The retrieval time.
        """
        # Measure time for retrieval
        start_time = time.time()
        context = retrieve_context_per_question(query, self.chunks_query_retriever)
        self.time_records['Retrieval'] = time.time() - start_time
        print(f"Retrieval Time: {self.time_records['Retrieval']:.2f} seconds")

        # Display the retrieved context
        show_context(context)


# Function to validate command line inputs
def validate_args(args):
    if args.chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if args.chunk_overlap < 0:
        raise ValueError("chunk_overlap must be a non-negative integer.")
    if args.n_retrieved <= 0:
        raise ValueError("n_retrieved must be a positive integer.")
    return args


# Function to parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Encode a PDF document and test RAG using ChromaDB vector database.")
    parser.add_argument("--path", type=str, default="../data/Understanding_Climate_Change.pdf",
                        help="Path to the PDF file to encode.")
    parser.add_argument("--chunk_size", type=int, default=1000,
                        help="Size of each text chunk (default: 1000).")
    parser.add_argument("--chunk_overlap", type=int, default=200,
                        help="Overlap between consecutive chunks (default: 200).")
    parser.add_argument("--n_retrieved", type=int, default=2,
                        help="Number of chunks to retrieve for each query (default: 2).")
    parser.add_argument("--query", type=str, default="What is the main cause of climate change?",
                        help="Query to test the retriever (default: 'What is the main cause of climate change?').")
    parser.add_argument("--persist_dir", type=str, default=None,
                        help="Path to directory for persisting ChromaDB storage.")
    parser.add_argument("--collection_name", type=str, default="rag_chroma",
                        help="Collection name for ChromaDB (default: 'rag_chroma').")
    parser.add_argument("--evaluate", action="store_true",
                        help="Whether to evaluate the retriever's performance (default: False).")

    # Parse and validate arguments
    return validate_args(parser.parse_args())


# Main function to handle argument parsing and call the ChromaDBRAG class
def main(args):
    # Initialize ChromaDBRAG
    chroma_rag = ChromaDBRAG(
        path=args.path,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        n_retrieved=args.n_retrieved,
        persist_directory=args.persist_dir,
        collection_name=args.collection_name
    )

    # Retrieve context based on the query
    chroma_rag.run(args.query)

    # Evaluate the retriever's performance on the query (if requested)
    if args.evaluate:
        evaluate_rag(chroma_rag.chunks_query_retriever)


if __name__ == '__main__':
    # Call the main function with parsed arguments
    main(parse_args())
