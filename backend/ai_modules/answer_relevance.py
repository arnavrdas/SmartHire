"""
ai_modules/answer_relevance.py
--------------------------------
Evaluates how well a candidate's answer addresses an interview question.

APPROACH — per-answer scoring with question-to-answer asymmetric comparison
---------------------------------------------------------------------------
The old approach compared all answers concatenated vs all questions
concatenated.  This was wrong for two reasons:

  1. "Tell me about yourself" and "I am Kuntal Pandya, I plan to get a job"
     have low cosine similarity because they're in different semantic spaces
     (interrogative vs declarative).  The model sees them as dissimilar even
     when the answer is correct.

  2. Dilution: a great answer to Q1 and a blank answer to Q5 averaged together
     hide both the strength and the weakness.

NEW APPROACH — three-signal scoring per Q/A pair:
  Signal 1 – Topic overlap (primary, 50%)
    Embed the question's KEY TOPIC (extracted by stripping question words) and
    the answer.  A good answer should live in the same semantic neighbourhood
    as the topic.

  Signal 2 – Substantiveness (30%)
    Penalise very short answers ("yes", "I don't know") and reward answers
    that are detailed.  Length alone isn't enough but <10 words is a red flag.
    Also checks whether common filler phrases dominate the answer.

  Signal 3 – Cross-encoder reranking (20%)
    The bi-encoder (all-MiniLM-L6-v2) is fast but blunt.  A cross-encoder
    reads the question and answer together and gives a fine-grained relevance
    score.  We use it as a soft signal if available; fall back to 0.5 if not.

Final relevance = weighted average of per-question scores (ignoring blanks).
"""

from __future__ import annotations
import re

# ── Cached models (lazy-loaded on first call) ─────────────────────────────────
_biencoder   = None
_crossencoder = None

# Filler phrases that indicate a non-answer
_FILLER = {
    "i don't know", "i do not know", "i have no idea", "no idea",
    "not sure", "i'm not sure", "i am not sure", "pass", "skip",
    "no answer", "n/a", "na", "nothing", "none",
}

# Question words to strip when extracting topic
_Q_WORDS = re.compile(
    r"^(tell me about|describe|explain|what (is|are|was|were)|"
    r"how (do|does|did|would|can)|where (do|did)|when (do|did)|"
    r"why (do|did|would)|who (is|was)|walk me through|"
    r"give me an example of|can you|could you|would you)\s+",
    re.IGNORECASE,
)


def _get_biencoder():
    global _biencoder
    if _biencoder is None:
        from sentence_transformers import SentenceTransformer
        _biencoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _biencoder


def _get_crossencoder():
    global _crossencoder
    if _crossencoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _crossencoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception:
            _crossencoder = None  # optional — fall back gracefully
    return _crossencoder


def _extract_topic(question: str) -> str:
    """Strip question words to get the core topic."""
    q = question.strip().rstrip("?").strip()
    q = _Q_WORDS.sub("", q)
    # Also strip leading "the" / "a" / "an"
    q = re.sub(r"^(the|a|an)\s+", "", q, flags=re.IGNORECASE)
    return q.strip() or question


def _substantiveness(answer: str) -> float:
    """
    How substantive is the answer?  Returns 0.0-1.0.

    - Pure filler ("I don't know", "pass") → 0.0
    - Very short (< 5 words) → 0.2
    - Short but not empty (5-15 words) → 0.5-0.7 (scaled linearly)
    - Normal (15-50 words) → 0.85
    - Detailed (50+ words) → 1.0
    """
    clean = answer.strip().lower()
    if not clean or clean in _FILLER:
        return 0.0

    words = clean.split()
    n = len(words)

    if n < 5:
        return 0.2
    if n < 15:
        return 0.5 + (n - 5) / 10 * 0.2   # 0.5 → 0.7
    if n < 50:
        return 0.7 + (n - 15) / 35 * 0.15  # 0.7 → 0.85
    return 1.0


def _topic_similarity(question: str, answer: str) -> float:
    """Cosine similarity between the question topic embedding and the answer."""
    from sentence_transformers import util
    model = _get_biencoder()
    topic = _extract_topic(question)
    embs = model.encode([topic, answer], convert_to_tensor=True)
    sim = util.pytorch_cos_sim(embs[0], embs[1]).item()
    # Cosine sim is naturally -1 to 1; clamp to 0-1 (negative = unrelated)
    return max(0.0, float(sim))


def _crossencoder_score(question: str, answer: str) -> float:
    """
    Fine-grained relevance using a cross-encoder.
    Returns 0.0-1.0.  Falls back to 0.5 if cross-encoder isn't available.
    """
    ce = _get_crossencoder()
    if ce is None:
        return 0.5
    try:
        raw = ce.predict([[question, answer]])[0]
        # ms-marco cross-encoder outputs a logit; convert via sigmoid
        import math
        score = 1.0 / (1.0 + math.exp(-raw))
        return float(score)
    except Exception:
        return 0.5


def score_single_answer(question: str, answer: str) -> float:
    """
    Score one answer against its question. Returns 0.0-1.0.

    Composed of:
      50% topic similarity  (bi-encoder cosine on topic phrase vs answer)
      30% substantiveness   (length + filler detection)
      20% cross-encoder     (fine-grained Q/A relevance, optional)
    """
    if not answer or not answer.strip():
        return 0.0
    if answer.startswith("["):           # "[No answer recorded]" markers
        return 0.0

    subst    = _substantiveness(answer)
    if subst == 0.0:
        return 0.0  # filler — skip expensive model calls

    topic    = _topic_similarity(question, answer)
    ce       = _crossencoder_score(question, answer)

    score    = topic * 0.50 + subst * 0.30 + ce * 0.20
    return round(min(1.0, max(0.0, score)), 4)


def evaluate_answer_relevance(
    candidate_answers: list[str] | str,
    questions: list[str] | str,
) -> dict:
    """
    Evaluate how well a candidate answered a set of interview questions.

    Accepts either:
      - Two lists (preferred): one answer per question, scored individually
      - Two strings (legacy):  concatenated text, scored as one blob

    Returns:
        {
          "relevance_score": float 0-1,     # overall weighted average
          "per_question":    list[float],   # individual scores (0-1 each)
          "answered_count":  int,           # questions with real answers
        }
    """
    # ── Normalise inputs ──────────────────────────────────────────────────────
    if isinstance(candidate_answers, str):
        # Legacy single-string path
        if not candidate_answers or not questions:
            return {"relevance_score": 0.0, "per_question": [], "answered_count": 0}
        score = score_single_answer(
            questions if isinstance(questions, str) else " ".join(questions),
            candidate_answers,
        )
        return {"relevance_score": score, "per_question": [score], "answered_count": 1 if score > 0 else 0}

    if not candidate_answers or not questions:
        return {"relevance_score": 0.0, "per_question": [], "answered_count": 0}

    # ── Per-question scoring ──────────────────────────────────────────────────
    pairs = list(zip(questions, candidate_answers))
    per_q_scores = []
    answered = 0

    for q, a in pairs:
        s = score_single_answer(q, a)
        per_q_scores.append(round(s, 4))
        if s > 0:
            answered += 1

    # Average only over answered questions (blank answers don't punish the
    # candidate — they simply don't contribute positively either)
    if answered == 0:
        avg = 0.0
    else:
        answered_scores = [s for s in per_q_scores if s > 0]
        avg = sum(answered_scores) / len(answered_scores)

    return {
        "relevance_score": round(avg, 4),
        "per_question":    per_q_scores,
        "answered_count":  answered,
    }


if __name__ == "__main__":
    qs = [
        "Tell me about yourself and your career goals.",
        "Describe a challenging project and how you overcame obstacles.",
        "What is your greatest professional achievement?",
    ]
    ans = [
        "I am a software engineer with 3 years of experience in Python and React. My goal is to become a full-stack engineer.",
        "I worked on a real-time analytics dashboard. The main challenge was handling 10k events per second. I solved it by switching to a streaming architecture with Kafka.",
        "I led a team that shipped a feature used by 100k users within 2 weeks of launch.",
    ]
    result = evaluate_answer_relevance(ans, qs)
    print("Overall:", result["relevance_score"])
    for q, a, s in zip(qs, ans, result["per_question"]):
        print(f"  {round(s*100)}  {q[:50]}")