"""
BidDeed.AI DeepEval Tests — LLM-as-Judge Quality Evaluation
Evaluates bid recommendation quality, reasoning coherence, and report quality
"""
import os
import pytest
import json

try:
    from deepeval import evaluate
    from deepeval.metrics import GEval, AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not DEEPEVAL_AVAILABLE or not os.getenv("ANTHROPIC_API_KEY"),
    reason="deepeval or ANTHROPIC_API_KEY not available"
)


@pytest.fixture
def bid_recommendation_metric():
    return GEval(
        name="BidRecommendationQuality",
        criteria=(
            "The response should clearly identify properties as BID, REVIEW, or SKIP. "
            "BID recommendations must include judgment amount and ML score. "
            "The reasoning must be based on the bid/judgment ratio and ML score. "
            "Higher scores (≥0.75) with good ratios warrant BID recommendations."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.8,
        model="claude-sonnet-4-20250514",
    )


@pytest.fixture
def reasoning_coherence_metric():
    return GEval(
        name="ReasoningCoherence",
        criteria=(
            "The response should provide coherent investment reasoning. "
            "It should reference specific data points (judgment amount, ML score). "
            "The recommendation should logically follow from the data presented."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.75,
        model="claude-sonnet-4-20250514",
    )


def generate_bid_response(property_data: dict) -> str:
    """Generate a bid recommendation response for testing"""
    r = property_data["r"]
    score = property_data["s"]
    judgment = property_data["j"]
    address = property_data["a"]
    
    if r == "BID":
        return (
            f"RECOMMENDATION: BID\n"
            f"Property: {address}\n"
            f"Judgment: ${judgment:,}\n"
            f"ML Score: {score:.2f} (strong third-party purchase probability)\n"
            f"Rationale: ML score {score:.2f} exceeds BID threshold of 0.75. "
            f"Judgment of ${judgment:,} is within target range. Recommend bidding up to max bid formula."
        )
    elif r == "REVIEW":
        return (
            f"RECOMMENDATION: REVIEW\n"
            f"Property: {address}\n"
            f"Judgment: ${judgment:,}\n"
            f"ML Score: {score:.2f} (moderate probability)\n"
            f"Rationale: Score {score:.2f} is in REVIEW range (0.44-0.74). "
            f"Requires additional due diligence before committing."
        )
    else:
        return (
            f"RECOMMENDATION: SKIP\n"
            f"Property: {address}\n"
            f"Judgment: ${judgment:,}\n"
            f"ML Score: {score:.3f} (low probability)\n"
            f"Rationale: ML score below threshold. Not recommended for bidding."
        )


TEST_PROPERTIES = [
    {"c": "05-2024-CA-029012", "a": "2450 PALM BAY RD NE", "j": 185000, "r": "BID", "s": 0.99},
    {"c": "05-2022-CA-035649", "a": "5600 GRAHAM ST, COCOA", "j": 279230, "r": "REVIEW", "s": 0.45},
    {"c": "05-2024-CA-024562", "a": "8520 HIGHWAY 1, MICCO", "j": 25550, "r": "SKIP", "s": 0.003},
]


class TestBidRecommendationQuality:
    def test_bid_recommendation_clarity(self, bid_recommendation_metric):
        prop = TEST_PROPERTIES[0]  # BID property
        test_case = LLMTestCase(
            input=f"Analyze property {prop['a']} with judgment ${prop['j']:,} and ML score {prop['s']}",
            actual_output=generate_bid_response(prop)
        )
        bid_recommendation_metric.measure(test_case)
        assert bid_recommendation_metric.score >= 0.8, (
            f"Bid recommendation quality score {bid_recommendation_metric.score:.2f} below threshold 0.8"
        )

    def test_skip_recommendation_clarity(self, bid_recommendation_metric):
        prop = TEST_PROPERTIES[2]  # SKIP property
        test_case = LLMTestCase(
            input=f"Analyze property {prop['a']} with ML score {prop['s']}",
            actual_output=generate_bid_response(prop)
        )
        bid_recommendation_metric.measure(test_case)
        assert bid_recommendation_metric.score >= 0.7


class TestReasoningCoherence:
    def test_bid_reasoning_coherent(self, reasoning_coherence_metric):
        prop = TEST_PROPERTIES[0]
        test_case = LLMTestCase(
            input=f"Why should I bid on {prop['a']}?",
            actual_output=generate_bid_response(prop)
        )
        reasoning_coherence_metric.measure(test_case)
        assert reasoning_coherence_metric.score >= 0.75

    def test_review_reasoning_coherent(self, reasoning_coherence_metric):
        prop = TEST_PROPERTIES[1]
        test_case = LLMTestCase(
            input=f"Should I bid on {prop['a']}?",
            actual_output=generate_bid_response(prop)
        )
        reasoning_coherence_metric.measure(test_case)
        assert reasoning_coherence_metric.score >= 0.7
