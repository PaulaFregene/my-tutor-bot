import os

import requests
from dotenv import load_dotenv

# load environment variables
load_dotenv()

API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
INDEX_ID = os.getenv("LLAMACLOUD_INDEX_ID")

RETRIEVE_URL = f"https://api.cloud.llamaindex.ai/api/v1/pipelines/{INDEX_ID}/retrieve"
CHAT_URL = "https://api.cloud.llamaindex.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def query_llamacloud(question: str, system_prompt: str):
    """
    Step 1: Retrieve relevant document chunks from LlamaCloud
    Step 2: Extract top 3 chunks
    Step 3: Send to LlamaCloud LLM with system prompt to generate answer
    """

    print(f"[STEP 1] Retrieving relevant documents for: {question[:100]}...")

    # Step 1: Retrieve documents
    try:
        response = requests.post(
            RETRIEVE_URL, headers=HEADERS, json={"query": question}, timeout=60
        )
        response.raise_for_status()
        data = response.json()
        print(f"[STEP 1] Retrieval response: {list(data.keys())}")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve from LlamaCloud: {e}")
        raise

    # Step 2: Extract top 3 chunks
    chunks = []
    if "retrieval_nodes" in data and data["retrieval_nodes"]:
        for node in data["retrieval_nodes"][:3]:  # Top 3 chunks only
            if "text" in node.get("node", {}):
                chunks.append(node["node"]["text"])

    if not chunks:
        print("[WARNING] No relevant chunks found")
        return "I cannot find relevant information in the course materials to answer your question."

    context = "\n\n---\n\n".join(chunks)
    print(
        f"[STEP 2] Extracted {len(chunks)} relevant chunks ({len(context)} characters)"
    )

    # Step 3: Call LlamaCloud LLM to synthesize answer
    print("[STEP 3] Generating answer with LlamaCloud LLM...")

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Using only the following course material:\n\n{context}\n\n---\n\nPlease answer this question: {question}",
        },
    ]

    try:
        llm_response = requests.post(
            CHAT_URL,
            headers=HEADERS,
            json={"messages": messages, "temperature": 0.7, "max_tokens": 1000},
            timeout=60,
        )
        llm_response.raise_for_status()
        result = llm_response.json()
        print(f"[STEP 3] LLM response received")
        print(f"[DEBUG] Response keys: {list(result.keys())}")

        # Extract answer from response
        if "choices" in result and len(result["choices"]) > 0:
            answer = result["choices"][0]["message"]["content"]
            print("[SUCCESS] Answer generated successfully")
            return answer
        elif "message" in result:
            # Alternative response format
            return result["message"]["content"]
        else:
            print(f"[ERROR] Unexpected LLM response format: {result}")
            return "Error: Could not generate response from LLM."

    except Exception as e:
        print(f"[ERROR] Failed to get LLM response: {e}")
        raise
