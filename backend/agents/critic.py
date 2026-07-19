"""
Critic Agent module for automated CI/CD pipeline failure investigation.
Performs rule-based verification of LLM Analysis results without calling external APIs.
"""

import logging
import os
import re
import sys
from typing import List, Set
from pydantic import BaseModel, Field

# Add project root to sys.path at startup to enable consistent imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Pydantic models for validation
from backend.services.llm_service import AnalysisResult
from backend.retrieval.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


class CriticResult(BaseModel):
    """
    Pydantic model representing the output of the Critic verification process.
    """
    approved: bool = Field(
        ..., 
        description="True if the analysis passes all heuristics and does not contain unsupported claims."
    )
    confidence_adjustment: int = Field(
        ..., 
        description="The recommended delta (positive or negative) to apply to the confidence score."
    )
    critic_comments: str = Field(
        ..., 
        description="Constructive critique, warnings, or audit findings."
    )
    missing_evidence: List[str] = Field(
        ..., 
        description="Specific gaps or cited files/evidence that were missing or incorrect."
    )


class CriticAgent:
    """
    Verifies LLM analysis results against retrieved documents using rule-based heuristics.
    Detects hallucinations, ensures grounded evidence, and evaluates confidence scores.
    """

    def __init__(self):
        """
        Initializes the CriticAgent with a set of English stop words to filter out
        during keyword intersection analysis.
        """
        self.stopwords: Set[str] = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
            "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont",
            "down", "during", "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have",
            "havent", "having", "he", "hed", "hell", "hes", "her", "here", "heres", "hers", "herself", "him",
            "himself", "his", "how", "hows", "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt",
            "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not",
            "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
            "over", "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so",
            "some", "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then",
            "there", "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those",
            "through", "to", "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well",
            "were", "weve", "werent", "what", "whats", "when", "whens", "where", "wheres", "which", "while",
            "who", "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll",
            "youre", "youve", "your", "yours", "yourself", "yourselves"
        }

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Splits text into lowercase alphanumeric words, filtering out common stop words.

        Args:
            text: Input string.

        Returns:
            A set of extracted keywords.
        """
        # Find all alphanumeric terms including hyphens, underscores, and dots (like package names)
        tokens = re.findall(r'\b[a-zA-Z0-9_\-\.]+\b', text.lower())
        return {t for t in tokens if t not in self.stopwords and len(t) > 2}

    def evaluate(
        self, 
        analysis: AnalysisResult, 
        retrieved_documents: List[RetrievedDocument]
    ) -> CriticResult:
        """
        Evaluates the AnalysisResult using strict rule-based rules.

        Args:
            analysis: The analysis output returned by the LLM.
            retrieved_documents: The original retrieved documents list.

        Returns:
            A CriticResult indicating approval, confidence adjustments, and comments.
        """
        approved = True
        confidence_adjustment = 0
        comments = []
        missing_evidence = []

        num_docs = len(retrieved_documents)

        # Heuristic 1: Check for index out-of-bounds (Direct Hallucination)
        invalid_indices = []
        for doc_idx in analysis.supporting_documents:
            if doc_idx < 1 or doc_idx > num_docs:
                invalid_indices.append(doc_idx)

        if invalid_indices:
            approved = False
            comments.append(f"REJECTED: Hallucinated supporting documents index: {invalid_indices}.")
            missing_evidence.append(f"Model cited non-existent document indices: {invalid_indices}.")
            confidence_adjustment -= 40

        # Heuristic 2: Verify if any evidence has been cited
        if not analysis.supporting_documents:
            approved = False
            comments.append("REJECTED: No supporting documents cited in analysis.")
            missing_evidence.append("Analysis must reference at least one valid retrieved document.")
            confidence_adjustment -= 30

        # Heuristic 3: Check if the explanation actually uses evidence from the cited documents
        valid_supporting_docs = [
            retrieved_documents[idx - 1] 
            for idx in analysis.supporting_documents 
            if 1 <= idx <= num_docs
        ]

        if valid_supporting_docs:
            # Aggregate all text from the valid cited evidence
            evidence_text = " ".join([
                f"{doc.chunk.content} {doc.chunk.source} {doc.chunk.title}"
                for doc in valid_supporting_docs
            ])
            evidence_keywords = self._extract_keywords(evidence_text)
            explanation_keywords = self._extract_keywords(analysis.explanation + " " + analysis.root_cause)

            # Check overlap between evidence keywords and explanation/root cause keywords
            overlap = evidence_keywords.intersection(explanation_keywords)
            if not overlap:
                approved = False
                comments.append("REJECTED: Explanation and root cause lack keyword alignment with the cited evidence.")
                missing_evidence.append("Explanation does not ground itself in the content of the cited documents.")
                confidence_adjustment -= 25
            else:
                comments.append(f"Evidence alignment verified (common terms: {list(overlap)[:5]}).")

        # Heuristic 4: Verify relation of suggested fixes to root cause
        rc_keywords = self._extract_keywords(analysis.root_cause)
        exp_keywords = self._extract_keywords(analysis.explanation)
        cause_keywords = rc_keywords.union(exp_keywords)

        if analysis.suggested_fixes:
            unrelated_fixes = []
            for i, fix in enumerate(analysis.suggested_fixes, 1):
                fix_keywords = self._extract_keywords(fix)
                # Check for overlapping keywords
                if not fix_keywords.intersection(cause_keywords):
                    unrelated_fixes.append(i)

            if len(unrelated_fixes) == len(analysis.suggested_fixes):
                comments.append("Warning: Suggested fixes are completely unaligned with root cause.")
                confidence_adjustment -= 15
            elif unrelated_fixes:
                comments.append(f"Warning: Suggested fixes at indices {unrelated_fixes} appear unrelated to root cause.")
                confidence_adjustment -= 5 * len(unrelated_fixes)
        else:
            comments.append("Warning: No suggested fixes provided.")
            confidence_adjustment -= 10

        # Heuristic 5: Evaluate confidence score realism
        # Penalize overconfidence (98%+ is usually unrealistic)
        if analysis.confidence > 98:
            confidence_adjustment -= 5
            comments.append("Confidence score calibrated down (100% is statistically overconfident).")

        # Penalize confidence if retrieved document scores (distances) are very high
        if valid_supporting_docs:
            avg_score = sum(doc.score for doc in valid_supporting_docs) / len(valid_supporting_docs)
            # A distance score of > 1.2 in FAISS suggests weak similarity matching
            if avg_score > 1.2 and analysis.confidence > 70:
                score_penalty = int((avg_score - 1.0) * 20)
                confidence_adjustment -= max(5, min(25, score_penalty))
                comments.append(f"Confidence penalized by {score_penalty} because retrieved evidence matches are weak (avg score: {avg_score:.2f}).")

        # Penalize brief explanations
        if len(analysis.explanation.strip()) < 30:
            confidence_adjustment -= 20
            comments.append("Confidence penalized because explanation text is too brief to substantiate claims.")

        # Aggregate comments
        critic_comments_str = " | ".join(comments) if comments else "Analysis verified successfully."

        return CriticResult(
            approved=approved,
            confidence_adjustment=confidence_adjustment,
            critic_comments=critic_comments_str,
            missing_evidence=missing_evidence
        )


if __name__ == "__main__":
    # Test suite covering good, hallucinated, and low-confidence answers
    from backend.retrieval.chunker import Chunk

    print("\n--- Running CriticAgent Test Suite ---")

    # Common mock retrieved documents
    mock_chunk_1 = Chunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        source="requirements.txt",
        title="Requirements dependencies",
        content="requests==2.31.0\npydantic==2.5.2",
        url="http://github.com/repo/requirements.txt",
        metadata={},
        chunk_index=1,
        total_chunks=1
    )
    doc_1 = RetrievedDocument(chunk=mock_chunk_1, score=0.1, rank=1)

    mock_chunk_2 = Chunk(
        chunk_id="chunk-2",
        document_id="doc-2",
        source="app.py",
        title="Main Application Loader",
        content="import requests\nfrom pydantic import BaseModel\n\nprint('Loaded successfully')",
        url="http://github.com/repo/app.py",
        metadata={},
        chunk_index=1,
        total_chunks=1
    )
    doc_2 = RetrievedDocument(chunk=mock_chunk_2, score=0.2, rank=2)

    docs = [doc_1, doc_2]
    critic = CriticAgent()

    # 1. Good Answer Case
    good_analysis = AnalysisResult(
        root_cause="requests dependency configuration in requirements.txt",
        confidence=90,
        explanation="The logs show import error for requests, and checking requirements.txt confirms requests is pinned at version 2.31.0. The code in app.py tries to import requests.",
        suggested_fixes=["Ensure requirements.txt is installed via pip install -r requirements.txt"],
        supporting_documents=[1, 2]
    )
    res_good = critic.evaluate(good_analysis, docs)
    print("\n[Case 1: Good Answer Evaluation]")
    print(res_good.model_dump_json(indent=2))
    assert res_good.approved is True, "Good answer should be approved"

    # 2. Hallucinated Answer Case (referencing index 3 which doesn't exist)
    hallucinated_analysis = AnalysisResult(
        root_cause="Missing redis dependency",
        confidence=100,
        explanation="The module redis was not found in docker-compose file.",
        suggested_fixes=["Install redis"],
        supporting_documents=[3] # Hallucinated document index
    )
    res_hallucinated = critic.evaluate(hallucinated_analysis, docs)
    print("\n[Case 2: Hallucinated Answer Evaluation]")
    print(res_hallucinated.model_dump_json(indent=2))
    assert res_hallucinated.approved is False, "Hallucinated answer should NOT be approved"

    # 3. Low Confidence Answer / Weak citation case
    low_confidence_analysis = AnalysisResult(
        root_cause="Unknown error",
        confidence=30,
        explanation="Too brief explanation.", # Penalized brief explanation
        suggested_fixes=[],
        supporting_documents=[] # No supporting evidence
    )
    res_low = critic.evaluate(low_confidence_analysis, docs)
    print("\n[Case 3: Low Confidence / No Evidence Answer Evaluation]")
    print(res_low.model_dump_json(indent=2))
    assert res_low.approved is False, "Answer without evidence should NOT be approved"

    print("\n[OK] Critic Agent test suite run completed.")
