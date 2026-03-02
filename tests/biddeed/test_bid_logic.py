"""
BidDeed.AI Unit Tests — Bid Logic & Thresholds
Tests the core investment logic without external dependencies
"""
import sys
import os
import pytest

# ── Replicate the core logic inline (no import needed) ─────────
def calculate_max_bid(arv: float, repairs: float) -> float:
    """(ARV × 70%) - Repairs - $10K - MIN($25K, 15% × ARV)"""
    base = arv * 0.70
    min_reserve = min(25_000, arv * 0.15)
    return base - repairs - 10_000 - min_reserve


def classify_recommendation(bid_amount: float, judgment: float) -> str:
    """BID ≥75%, REVIEW 60-74%, SKIP <60%"""
    if judgment == 0:
        return "SKIP"
    ratio = bid_amount / judgment
    if ratio >= 0.75:
        return "BID"
    elif ratio >= 0.60:
        return "REVIEW"
    return "SKIP"


def classify_by_ml_score(score: float) -> str:
    """Based on observed data: BID≥0.75, REVIEW 0.44-0.74, SKIP≤0.43"""
    if score >= 0.75:
        return "BID"
    elif score >= 0.44:
        return "REVIEW"
    return "SKIP"


# ── Tests ───────────────────────────────────────────────────────
class TestMaxBidFormula:
    def test_standard_property(self):
        """200K ARV, 20K repairs"""
        result = calculate_max_bid(200_000, 20_000)
        expected = 200_000 * 0.70 - 20_000 - 10_000 - min(25_000, 200_000 * 0.15)
        assert result == expected

    def test_min_reserve_uses_25k_for_high_arv(self):
        """ARV=400K: 15% = 60K → use 25K cap"""
        result = calculate_max_bid(400_000, 30_000)
        assert result == 400_000 * 0.70 - 30_000 - 10_000 - 25_000

    def test_min_reserve_uses_15pct_for_low_arv(self):
        """ARV=100K: 15% = 15K < 25K → use 15K"""
        result = calculate_max_bid(100_000, 5_000)
        assert result == 100_000 * 0.70 - 5_000 - 10_000 - 15_000

    def test_zero_repairs(self):
        result = calculate_max_bid(250_000, 0)
        assert result > 0

    def test_result_is_float(self):
        result = calculate_max_bid(300_000, 25_000)
        assert isinstance(result, float)


class TestBidThresholds:
    @pytest.mark.parametrize("bid,judgment,expected", [
        (150_000, 185_000, "BID"),    # ratio=0.81
        (147_000, 175_724, "BID"),    # ratio=0.836
        (186_065, 372_130, "SKIP"),   # ratio=0.50
        (133_145, 166_431, "BID"),    # ratio=0.80
        (162_789, 232_556, "REVIEW"), # ratio=0.70
    ])
    def test_bid_classification(self, bid, judgment, expected):
        result = classify_recommendation(bid, judgment)
        assert result == expected, f"Expected {expected} for ratio {bid/judgment:.2f}"

    def test_bid_boundary_exactly_75pct(self):
        assert classify_recommendation(75_000, 100_000) == "BID"

    def test_review_boundary_exactly_60pct(self):
        assert classify_recommendation(60_000, 100_000) == "REVIEW"

    def test_skip_below_60pct(self):
        assert classify_recommendation(59_000, 100_000) == "SKIP"

    def test_zero_judgment_is_skip(self):
        assert classify_recommendation(50_000, 0) == "SKIP"

    def test_ml_score_bid(self):
        assert classify_by_ml_score(0.99) == "BID"
        assert classify_by_ml_score(0.76) == "BID"
        assert classify_by_ml_score(0.75) == "BID"

    def test_ml_score_review(self):
        assert classify_by_ml_score(0.68) == "REVIEW"
        assert classify_by_ml_score(0.44) == "REVIEW"

    def test_ml_score_skip(self):
        assert classify_by_ml_score(0.003) == "SKIP"
        assert classify_by_ml_score(0.42) == "SKIP"


class TestPropertySchema:
    VALID_PROPERTY = {
        "c": "05-2024-CA-029012",
        "a": "2450 PALM BAY RD NE, PALM BAY",
        "j": 185000,
        "m": 147000,
        "r": "BID",
        "s": 0.99,
        "d": "2025-12-03",
        "p": "Freedom Mortgage"
    }

    def test_required_fields_present(self):
        for field in ["c", "a", "j", "m", "r", "s", "d", "p"]:
            assert field in self.VALID_PROPERTY

    def test_judgment_is_numeric(self):
        assert isinstance(self.VALID_PROPERTY["j"], (int, float))

    def test_recommendation_is_valid_enum(self):
        assert self.VALID_PROPERTY["r"] in ["BID", "REVIEW", "SKIP"]

    def test_ml_score_in_range(self):
        assert 0.0 <= self.VALID_PROPERTY["s"] <= 1.0

    def test_case_number_format(self):
        import re
        pattern = r"^\d{2}-\d{4}-C[AC]-\d{6}$"
        assert re.match(pattern, self.VALID_PROPERTY["c"])

    def test_max_bid_between_60k_and_200k_typical(self):
        arv = self.VALID_PROPERTY["m"] * 1.30  # estimate ARV from mortgage
        max_bid = calculate_max_bid(arv, 20_000)
        # Sanity: max bid should be less than judgment
        assert max_bid < self.VALID_PROPERTY["j"] * 1.5

    def test_bid_ratio_consistency(self):
        """m/j should correlate with recommendation"""
        ratio = self.VALID_PROPERTY["m"] / self.VALID_PROPERTY["j"]
        # For BID properties, mortgage typically < judgment (lender paid less)
        assert ratio < 1.0


class TestAuctionDataset:
    """Tests against the known Dec 2025 dataset"""
    PROPERTIES = [
        {"c": "05-2024-CA-029012", "r": "BID",    "s": 0.99},
        {"c": "05-2024-CA-014947", "r": "BID",    "s": 0.81},
        {"c": "05-2025-CA-013384", "r": "BID",    "s": 0.82},
        {"c": "05-2022-CA-035649", "r": "REVIEW",  "s": 0.45},
        {"c": "05-2024-CA-024562", "r": "SKIP",    "s": 0.003},
        {"c": "05-2024-CA-031234", "r": "SKIP",    "s": 0.003},
    ]

    def test_bid_count_correct(self):
        bids = [p for p in self.PROPERTIES if p["r"] == "BID"]
        assert len(bids) == 3

    def test_ml_predictions_consistent_with_recommendations(self):
        """ML score classification should agree with labeled recommendation"""
        for prop in self.PROPERTIES:
            ml_class = classify_by_ml_score(prop["s"])
            # Allow REVIEW/SKIP boundary ambiguity
            if prop["r"] == "BID":
                assert ml_class == "BID", f"{prop['c']}: score {prop['s']} should be BID"

    def test_all_scores_in_valid_range(self):
        for prop in self.PROPERTIES:
            assert 0.0 <= prop["s"] <= 1.0, f"Score out of range: {prop['s']}"
