# pyrefly: ignore [missing-import]
from langchain_community.document_loaders import PyPDFLoader
# pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter
# pyrefly: ignore [missing-import]
from langchain_openai import OpenAIEmbeddings
# pyrefly: ignore [missing-import]
from langchain_community.vectorstores import FAISS
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from langchain_core.prompts import PromptTemplate
# pyrefly: ignore [missing-import]
from openai import RateLimitError
from typing import List
# pyrefly: ignore [missing-import]
from rank_bm25 import BM25Okapi
# pyrefly: ignore [missing-import]
import fitz
import asyncio
import random
import textwrap
import numpy as np
import os
from enum import Enum
from langchain_core.documents import Document


def replace_t_with_space(list_of_documents):
    """
    Replaces all tab characters ('\t') with spaces in the page content of each document

    Args:
        list_of_documents: A list of document objects, each with a 'page_content' attribute.

    Returns:
        The modified list of documents with tab characters replaced by spaces.
    """

    for doc in list_of_documents:
        doc.page_content = doc.page_content.replace('\t', ' ')  # Replace tabs with spaces
    return list_of_documents


def text_wrap(text, width=120):
    """
    Wraps the input text to the specified width.

    Args:
        text (str): The input text to wrap.
        width (int): The width at which to wrap the text.

    Returns:
        str: The wrapped text.
    """
    return textwrap.fill(text, width=width)


def encode_pdf(path, chunk_size=1000, chunk_overlap=200, vectorstore_type="chroma", persist_directory=None, collection_name="rag_collection", embedding_model=None):
    """
    Encodes a PDF book into a vector store using default or custom embeddings.

    Args:
        path: The path to the PDF file.
        chunk_size: The desired size of each text chunk.
        chunk_overlap: The amount of overlap between consecutive chunks.
        vectorstore_type: Type of vector store ("chroma" or "faiss"). Default is "chroma".
        persist_directory: Optional path to save persistent vector storage (Chroma).
        collection_name: Collection name for Chroma DB.
        embedding_model: Optional custom embedding model instance.

    Returns:
        A Chroma or FAISS vector store containing the encoded book content.
    """

    # Load PDF documents using PyMuPDF (fitz) for high performance & reliability
    try:
        pdf_doc = fitz.open(path)
        documents = []
        for page_num in range(len(pdf_doc)):
            page_text = pdf_doc[page_num].get_text()
            if page_text and page_text.strip():
                documents.append(Document(page_content=page_text, metadata={"page": page_num, "source": path}))
        pdf_doc.close()
    except Exception as e:
        # Fallback to PyPDFLoader if fitz encounters issues
        try:
            loader = PyPDFLoader(path)
            documents = loader.load()
        except Exception as inner_e:
            raise RuntimeError(f"Failed to read PDF file '{os.path.basename(path)}': {str(e)} / {str(inner_e)}")

    if not documents:
        raise ValueError(
            f"No extractable text found in '{os.path.basename(path)}'. "
            "If this is a scanned document or image PDF, OCR is required before processing."
        )

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    texts = text_splitter.split_documents(documents)
    cleaned_texts = replace_t_with_space(texts)

    # Create embeddings and vector store
    embeddings = embedding_model if embedding_model is not None else get_default_embeddings()
    if vectorstore_type.lower() == "faiss":
        vectorstore = FAISS.from_documents(cleaned_texts, embeddings)
    else:
        kwargs = {"documents": cleaned_texts, "embedding": embeddings, "collection_name": collection_name}
        if persist_directory:
            kwargs["persist_directory"] = persist_directory
        vectorstore = Chroma.from_documents(**kwargs)

    return vectorstore


def encode_from_string(content, chunk_size=1000, chunk_overlap=200, vectorstore_type="chroma", persist_directory=None, collection_name="rag_collection", embedding_model=None):
    """
    Encodes a string into a vector store using default or custom embeddings.

    Args:
        content (str): The text content to be encoded.
        chunk_size (int): The size of each chunk of text.
        chunk_overlap (int): The overlap between chunks.
        vectorstore_type (str): Type of vector store ("chroma" or "faiss"). Default is "chroma".
        persist_directory (str): Optional directory path for Chroma DB persistence.
        collection_name (str): Collection name for Chroma DB.
        embedding_model: Optional custom embedding model instance.

    Returns:
        VectorStore: A Chroma or FAISS vector store containing the encoded content.

    Raises:
        ValueError: If the input content is not valid.
        RuntimeError: If there is an error during the encoding process.
    """

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Content must be a non-empty string.")

    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")

    if not isinstance(chunk_overlap, int) or chunk_overlap < 0:
        raise ValueError("chunk_overlap must be a non-negative integer.")

    try:
        # Split the content into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.create_documents([content])

        # Assign metadata to each chunk
        for chunk in chunks:
            chunk.metadata['relevance_score'] = 1.0

        # Generate embeddings and create the vector store
        embeddings = embedding_model if embedding_model is not None else get_default_embeddings()
        if vectorstore_type.lower() == "faiss":
            vectorstore = FAISS.from_documents(chunks, embeddings)
        else:
            kwargs = {"documents": chunks, "embedding": embeddings, "collection_name": collection_name}
            if persist_directory:
                kwargs["persist_directory"] = persist_directory
            vectorstore = Chroma.from_documents(**kwargs)

    except Exception as e:
        raise RuntimeError(f"An error occurred during the encoding process: {str(e)}")

    return vectorstore


def retrieve_context_per_question(question, chunks_query_retriever):
    """
    Retrieves relevant context and unique URLs for a given question using the chunks query retriever.

    Args:
        question: The question for which to retrieve context and URLs.

    Returns:
        A tuple containing:
        - A string with the concatenated content of relevant documents.
        - A list of unique URLs from the metadata of the relevant documents.
    """

    # Retrieve relevant documents for the given question
    if hasattr(chunks_query_retriever, "invoke"):
        docs = chunks_query_retriever.invoke(question)
    else:
        docs = chunks_query_retriever.get_relevant_documents(question)

    # Concatenate document content
    context = [doc.page_content for doc in docs]

    return context


class QuestionAnswerFromContext(BaseModel):
    """
    Model to generate an answer to a query based on a given context.
    
    Attributes:
        answer_based_on_content (str): The generated answer based on the context.
    """
    answer_based_on_content: str = Field(description="Generates an answer to a query based on a given context.")


from langchain_core.output_parsers import StrOutputParser

def create_question_answer_from_context_chain(llm):
    question_answer_from_context_llm = llm

    question_answer_prompt_template = """You are a precise AI assistant. Answer the question using ONLY the facts directly mentioned in the context below.

Formatting Guidelines:
- Format your response cleanly using Markdown with clear headers (###), bullet points, and key highlights.
- Highlight important metrics, numbers, scores, and names using **bold text** or `code formatting`.
- Use Markdown tables (| Column | Column |) when presenting multiple structured facts or scores.
- Use callout quotes (> Note:) for important disclaimers or missing details.
- Do NOT output raw source markers, page numbers, or unformatted wall-of-text blocks.
- If the question cannot be answered from the context, state clearly using an informational callout (> ℹ️) that the document does not contain that information.

Context:
{context}

Question:
{question}

Answer:"""

    question_answer_from_context_prompt = PromptTemplate(
        template=question_answer_prompt_template,
        input_variables=["context", "question"],
    )

    chain = question_answer_from_context_prompt | question_answer_from_context_llm | StrOutputParser()
    return chain


def answer_question_from_context(question, context, question_answer_from_context_chain):
    """
    Answer a question using the given context by invoking a chain of reasoning.

    Args:
        question: The question to be answered.
        context: The context to be used for answering the question.

    Returns:
        A dictionary containing the answer, context, and question.
    """
    input_data = {
        "question": question,
        "context": context
    }
    print("Answering the question from the retrieved context...")

    output = question_answer_from_context_chain.invoke(input_data)
    answer = str(output).strip()
    return {"answer": answer, "context": context, "question": question}


def show_context(context):
    """
    Display the contents of the provided context list.

    Args:
        context (list): A list of context items to be displayed.

    Prints each context item in the list with a heading indicating its position.
    """
    for i, c in enumerate(context):
        print(f"Context {i + 1}:")
        print(c)
        print("\n")


def read_pdf_to_string(path):
    """
    Read a PDF document from the specified path and return its content as a string.

    Args:
        path (str): The file path to the PDF document.

    Returns:
        str: The concatenated text content of all pages in the PDF document.

    The function uses the 'fitz' library (PyMuPDF) to open the PDF document, iterate over each page,
    extract the text content from each page, and append it to a single string.
    """
    # Open the PDF document located at the specified path
    doc = fitz.open(path)
    content = ""
    # Iterate over each page in the document
    for page_num in range(len(doc)):
        # Get the current page
        page = doc[page_num]
        # Extract the text content from the current page and append it to the content string
        content += page.get_text()
    return content


def bm25_retrieval(bm25: BM25Okapi, cleaned_texts: List[str], query: str, k: int = 5) -> List[str]:
    """
    Perform BM25 retrieval and return the top k cleaned text chunks.

    Args:
    bm25 (BM25Okapi): Pre-computed BM25 index.
    cleaned_texts (List[str]): List of cleaned text chunks corresponding to the BM25 index.
    query (str): The query string.
    k (int): The number of text chunks to retrieve.

    Returns:
    List[str]: The top k cleaned text chunks based on BM25 scores.
    """
    # Tokenize the query
    query_tokens = query.split()

    # Get BM25 scores for the query
    bm25_scores = bm25.get_scores(query_tokens)

    # Get the indices of the top k scores
    top_k_indices = np.argsort(bm25_scores)[::-1][:k]

    # Retrieve the top k cleaned text chunks
    top_k_texts = [cleaned_texts[i] for i in top_k_indices]

    return top_k_texts


async def exponential_backoff(attempt):
    """
    Implements exponential backoff with a jitter.
    
    Args:
        attempt: The current retry attempt number.
        
    Waits for a period of time before retrying the operation.
    The wait time is calculated as (2^attempt) + a random fraction of a second.
    """
    # Calculate the wait time with exponential backoff and jitter
    wait_time = (2 ** attempt) + random.uniform(0, 1)
    print(f"Rate limit hit. Retrying in {wait_time:.2f} seconds...")

    # Asynchronously sleep for the calculated wait time
    await asyncio.sleep(wait_time)


async def retry_with_exponential_backoff(coroutine, max_retries=5):
    """
    Retries a coroutine using exponential backoff upon encountering a RateLimitError.
    
    Args:
        coroutine: The coroutine to be executed.
        max_retries: The maximum number of retry attempts.
        
    Returns:
        The result of the coroutine if successful.
        
    Raises:
        The last encountered exception if all retry attempts fail.
    """
    for attempt in range(max_retries):
        try:
            # Attempt to execute the coroutine
            return await coroutine
        except RateLimitError as e:
            # If the last attempt also fails, raise the exception
            if attempt == max_retries - 1:
                raise e

            # Wait for an exponential backoff period before retrying
            await exponential_backoff(attempt)

    # If max retries are reached without success, raise an exception
    raise Exception("Max retries reached")


import os

def get_default_embeddings():
    """
    Returns default embeddings model. Uses local HuggingFaceEmbeddings ('all-MiniLM-L6-v2')
    for vector storage to ensure 100% reliable local document search without API key dependencies.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    except Exception:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


# Enum class representing different embedding providers
class EmbeddingProvider(Enum):
    OPENAI = "openai"
    COHERE = "cohere"
    AMAZON_BEDROCK = "bedrock"
    GEMINI = "gemini"
    GOOGLE = "google"

# Enum class representing different model providers
class ModelProvider(Enum):
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    AMAZON_BEDROCK = "bedrock"
    GEMINI = "gemini"
    GOOGLE = "google"


def get_langchain_embedding_provider(provider: EmbeddingProvider, model_id: str = None):
    """
    Returns an embedding provider based on the specified provider and model ID.
    """
    provider_val = provider.value if isinstance(provider, Enum) else str(provider).lower()
    if provider_val == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings()
    elif provider_val in ("gemini", "google"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        model = model_id if model_id else "models/gemini-embedding-001"
        return GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
    elif provider_val == "cohere":
        from langchain_cohere import CohereEmbeddings
        return CohereEmbeddings()
    elif provider_val == "bedrock":
        from langchain_community.embeddings import BedrockEmbeddings
        return BedrockEmbeddings(model_id=model_id) if model_id else BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def get_langchain_model_provider(provider: ModelProvider, model_id: str = None):
    """
    Returns an LLM model provider based on the specified provider and model ID.
    """
    provider_val = provider.value if isinstance(provider, Enum) else str(provider).lower()
    if provider_val == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_id or "gpt-4o-mini")
    elif provider_val in ("gemini", "google"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY. Please set GEMINI_API_KEY in .env.")
        model_name = model_id or "gemini-3.5-flash"
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
