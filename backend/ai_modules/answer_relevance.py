from sentence_transformers import SentenceTransformer, util

# Load model once at module level
model = SentenceTransformer('all-MiniLM-L6-v2')

def evaluate_answer_relevance(candidate_answer: str, expected_answer: str) -> dict:
    """
    Evaluate semantic similarity between candidate's answer and expected answer.
    
    Args:
        candidate_answer (str): The answer provided by the candidate
        expected_answer (str): The ideal or reference answer
    
    Returns:
        dict: Relevance score (0–1)
    """
    if not candidate_answer or not expected_answer:
        return {"relevance_score": 0.0}

    # Encode both answers
    embeddings = model.encode([candidate_answer, expected_answer], convert_to_tensor=True)

    # Compute cosine similarity
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()

    return {
        "relevance_score": round(similarity, 3)
    }

if __name__ == "__main__":
    # Example usage
    candidate = "I have experience working with Python and building REST APIs."
    expected = "The candidate should know Python and FastAPI for backend development."
    output = evaluate_answer_relevance(candidate, expected)
    print(output)
