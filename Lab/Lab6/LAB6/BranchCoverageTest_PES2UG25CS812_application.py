import pytest
from credit_card_rewards import reward_points, late_payment_fee, card_status


# =====================================================================
# Branch Coverage Tests for reward_points()
# =====================================================================

def test_reward_points_card_tier_branches():
    # Decision: if card_tier not in POINTS_PER_100
    # TRUE branch: unknown card tier raises ValueError
    with pytest.raises(ValueError, match="unknown card tier"):
        reward_points("diamond", 1000, "shopping", False)

    # FALSE branch: known card tiers proceed
    assert reward_points("classic", 100, "shopping", False) == 1
    assert reward_points("gold", 100, "shopping", False) == 2
    assert reward_points("platinum", 100, "shopping", False) == 4


def test_reward_points_amount_validation_branches():
    # Decision: if amount <= 0
    # TRUE branch: amount is 0 or negative raises ValueError
    with pytest.raises(ValueError, match="invalid amount"):
        reward_points("classic", 0, "shopping", False)
    with pytest.raises(ValueError, match="invalid amount"):
        reward_points("classic", -50, "shopping", False)

    # FALSE branch: positive amount proceeds
    assert reward_points("classic", 200, "shopping", False) == 2


def test_reward_points_fuel_category_branches():
    # Decision: if category == "fuel"
    # TRUE branch: fuel spend returns 0 immediately
    assert reward_points("gold", 500, "fuel", False) == 0

    # FALSE branch: non-fuel spend proceeds to calculate points
    assert reward_points("gold", 500, "shopping", False) == 10


def test_reward_points_category_multiplier_branches():
    # Decision: if category == "dining" or category == "travel"
    # TRUE branch via "dining": points are doubled
    assert reward_points("classic", 100, "dining", False) == 2  # 1 * 2 = 2

    # TRUE branch via "travel": points are doubled
    assert reward_points("classic", 100, "travel", False) == 2  # 1 * 2 = 2

    # FALSE branch (neither dining nor travel): points not doubled
    assert reward_points("classic", 100, "entertainment", False) == 1


def test_reward_points_weekend_bonus_branches():
    # Decision: if is_weekend and card_tier != "classic"
    # TRUE branch: is_weekend is True and card_tier is non-classic (e.g. gold, platinum) -> +50
    assert reward_points("gold", 100, "shopping", True) == 52       # (1 * 2) + 50 = 52
    assert reward_points("platinum", 100, "shopping", True) == 54   # (1 * 4) + 50 = 54

    # FALSE branch 1: is_weekend is True, but card_tier IS "classic" -> no bonus
    assert reward_points("classic", 100, "shopping", True) == 1

    # FALSE branch 2: is_weekend is False, card_tier is non-classic -> no bonus
    assert reward_points("gold", 100, "shopping", False) == 2

    # FALSE branch 3: is_weekend is False, card_tier IS "classic" -> no bonus
    assert reward_points("classic", 100, "shopping", False) == 1


# =====================================================================
# Branch Coverage Tests for late_payment_fee()
# =====================================================================

def test_late_payment_fee_validation_branches():
    # Decision: if days_late <= 0 or outstanding <= 0
    # TRUE branch 1: days_late == 0 (on-time payment)
    assert late_payment_fee(5000, 0) == 0

    # TRUE branch 2: days_late < 0 (early/advance payment)
    assert late_payment_fee(5000, -3) == 0

    # TRUE branch 3: days_late > 0, but outstanding == 0
    assert late_payment_fee(0, 10) == 0

    # TRUE branch 4: days_late > 0, but outstanding < 0 (credit balance)
    assert late_payment_fee(-200, 10) == 0

    # FALSE branch: both days_late > 0 and outstanding > 0 -> proceeds to fee calculation
    assert late_payment_fee(500, 5) == 100


def test_late_payment_fee_tier_branches():
    # Decision: if outstanding <= 1000
    # TRUE branch: outstanding <= 1000 -> fee = 100
    assert late_payment_fee(1000, 10) == 100

    # FALSE branch of (outstanding <= 1000) leading to elif outstanding <= 10000:
    # TRUE branch of elif: 1000 < outstanding <= 10000 -> fee = 500
    assert late_payment_fee(1001, 10) == 500
    assert late_payment_fee(10000, 10) == 500

    # FALSE branch of elif leading to else: outstanding > 10000 -> fee = 1000
    assert late_payment_fee(10001, 10) == 1000


def test_late_payment_fee_surcharge_branches():
    # Decision: if days_late > 30
    # FALSE branch: days_late <= 30 -> no surcharge (+0)
    assert late_payment_fee(1000, 30) == 100
    assert late_payment_fee(5000, 1) == 500

    # TRUE branch: days_late > 30 -> surcharge applied (+750)
    assert late_payment_fee(1000, 31) == 850
    assert late_payment_fee(5000, 45) == 1250


# =====================================================================
# Branch Coverage Tests for card_status()
# =====================================================================

def test_card_status_frozen_branch():
    # Decision: if is_frozen
    # TRUE branch: returns "frozen"
    assert card_status(50, 0, True) == "frozen"

    # FALSE branch: proceeds to check missed payments
    assert card_status(50, 0, False) != "frozen"


def test_card_status_missed_payments_blocked_branch():
    # Decision: if missed_payments >= 3
    # TRUE branch: returns "blocked"
    assert card_status(20, 3, False) == "blocked"
    assert card_status(20, 4, False) == "blocked"

    # FALSE branch: missed_payments < 3, proceeds to check utilisation
    assert card_status(20, 2, False) != "blocked"


def test_card_status_utilisation_over_limit_branch():
    # Decision: if utilisation_percent > 90
    # TRUE branch: returns "over limit risk"
    assert card_status(91, 0, False) == "over limit risk"
    assert card_status(95, 2, False) == "over limit risk"

    # FALSE branch: utilisation_percent <= 90, proceeds to check watch conditions
    assert card_status(90, 0, False) != "over limit risk"


def test_card_status_watch_and_good_branches():
    # Decision: elif utilisation_percent > 30 or missed_payments > 0
    # TRUE branch via utilisation_percent > 30 (with missed_payments == 0): returns "watch"
    assert card_status(31, 0, False) == "watch"
    assert card_status(90, 0, False) == "watch"

    # TRUE branch via missed_payments > 0 (with utilisation_percent <= 30): returns "watch"
    assert card_status(30, 1, False) == "watch"
    assert card_status(10, 2, False) == "watch"

    # FALSE branch: utilisation_percent <= 30 and missed_payments <= 0 -> returns "good"
    assert card_status(30, 0, False) == "good"
    assert card_status(0, 0, False) == "good"


def test_card_status_condition_priorities():
    # Priority 1: is_frozen overrides missed_payments >= 3 and utilisation > 90
    assert card_status(95, 4, True) == "frozen"

    # Priority 2: missed_payments >= 3 overrides utilisation > 90 when not frozen
    assert card_status(95, 3, False) == "blocked"

