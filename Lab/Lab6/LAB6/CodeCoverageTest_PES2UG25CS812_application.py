import pytest
from credit_card_rewards import reward_points, late_payment_fee, card_status


# =====================================================================
# Tests for reward_points()
# =====================================================================

def test_reward_points_invalid_tier():
    with pytest.raises(ValueError, match="unknown card tier"):
        reward_points("silver", 500, "shopping", False)

    with pytest.raises(ValueError, match="unknown card tier"):
        reward_points("", 500, "shopping", False)


def test_reward_points_invalid_amount():
    with pytest.raises(ValueError, match="invalid amount"):
        reward_points("classic", 0, "shopping", False)

    with pytest.raises(ValueError, match="invalid amount"):
        reward_points("gold", -100, "shopping", False)


def test_reward_points_fuel_returns_zero():
    # Fuel spend always earns 0 points regardless of tier or weekend
    assert reward_points("classic", 1000, "fuel", False) == 0
    assert reward_points("platinum", 2500, "fuel", True) == 0


def test_reward_points_tier_multipliers():
    # Base rates: classic=1, gold=2, platinum=4 per 100 spent
    assert reward_points("classic", 500, "electronics", False) == 5
    assert reward_points("gold", 500, "electronics", False) == 10
    assert reward_points("platinum", 500, "electronics", False) == 20


def test_reward_points_amount_below_100():
    # Amount below 100 integer divides to 0
    assert reward_points("classic", 50, "groceries", False) == 0
    assert reward_points("gold", 99, "groceries", False) == 0


def test_reward_points_category_multipliers():
    # Dining gives 2x multiplier
    assert reward_points("gold", 300, "dining", False) == 12  # (3 * 2) * 2 = 12
    # Travel gives 2x multiplier
    assert reward_points("platinum", 200, "travel", False) == 16  # (2 * 4) * 2 = 16


def test_reward_points_weekend_bonus():
    # Gold on weekend gets +50 points
    assert reward_points("gold", 200, "groceries", True) == 54  # (2 * 2) + 50 = 54
    # Platinum on weekend gets +50 points
    assert reward_points("platinum", 200, "groceries", True) == 58  # (2 * 4) + 50 = 58
    # Classic on weekend does NOT get weekend bonus
    assert reward_points("classic", 200, "groceries", True) == 2  # (2 * 1) = 2
    # Dining + weekend bonus combined on gold
    assert reward_points("gold", 200, "dining", True) == 58  # ((2 * 2) * 2) + 50 = 58


# =====================================================================
# Tests for late_payment_fee()
# =====================================================================

def test_late_payment_fee_zero_or_negative_days_late():
    assert late_payment_fee(1000, 0) == 0
    assert late_payment_fee(1000, -5) == 0


def test_late_payment_fee_zero_or_negative_outstanding():
    assert late_payment_fee(0, 10) == 0
    assert late_payment_fee(-500, 10) == 0


def test_late_payment_fee_tier_up_to_1000():
    # Outstanding <= 1000 fee is 100
    assert late_payment_fee(500, 10) == 100
    assert late_payment_fee(1000, 10) == 100


def test_late_payment_fee_tier_1001_to_10000():
    # Outstanding 1001 to 10000 fee is 500
    assert late_payment_fee(1001, 10) == 500
    assert late_payment_fee(5000, 10) == 500
    assert late_payment_fee(10000, 10) == 500


def test_late_payment_fee_tier_above_10000():
    # Outstanding > 10000 fee is 1000
    assert late_payment_fee(10001, 10) == 1000
    assert late_payment_fee(25000, 10) == 1000


def test_late_payment_fee_surcharge_after_30_days():
    # At day 30: no surcharge
    assert late_payment_fee(1000, 30) == 100
    assert late_payment_fee(5000, 30) == 500
    assert late_payment_fee(15000, 30) == 1000

    # At day 31: surcharge of +750 applies
    assert late_payment_fee(1000, 31) == 850
    assert late_payment_fee(5000, 31) == 1250
    assert late_payment_fee(15000, 31) == 1750


# =====================================================================
# Tests for card_status()
# =====================================================================

def test_card_status_frozen():
    # is_frozen overrides everything else
    assert card_status(50, 0, True) == "frozen"
    assert card_status(99, 5, True) == "frozen"


def test_card_status_blocked():
    # missed_payments >= 3 leads to blocked when not frozen
    assert card_status(20, 3, False) == "blocked"
    assert card_status(95, 4, False) == "blocked"


def test_card_status_over_limit_risk():
    # utilisation_percent > 90 leads to over limit risk when missed_payments < 3
    assert card_status(91, 0, False) == "over limit risk"
    assert card_status(95, 2, False) == "over limit risk"


def test_card_status_watch():
    # utilisation_percent > 30 and <= 90
    assert card_status(31, 0, False) == "watch"
    assert card_status(90, 0, False) == "watch"
    # or missed_payments > 0 (and < 3) with utilisation <= 30
    assert card_status(20, 1, False) == "watch"
    assert card_status(30, 2, False) == "watch"


def test_card_status_good():
    # utilisation_percent <= 30 and missed_payments == 0
    assert card_status(0, 0, False) == "good"
    assert card_status(30, 0, False) == "good"

