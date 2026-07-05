"""Tests for distance tier computation."""
from src.pet.distance_tier import compute_tier


def test_tier_near():
    tier, scale = compute_tier(bbox_w=200)
    assert tier == "near"
    assert scale == 1.5


def test_tier_near_boundary():
    tier, scale = compute_tier(bbox_w=160)
    assert tier == "near"
    assert scale == 1.5


def test_tier_mid():
    tier, scale = compute_tier(bbox_w=120)
    assert tier == "mid"
    assert scale == 1.0


def test_tier_mid_boundary():
    tier, scale = compute_tier(bbox_w=80)
    assert tier == "mid"
    assert scale == 1.0


def test_tier_far():
    tier, scale = compute_tier(bbox_w=40)
    assert tier == "far"
    assert scale == 0.6


def test_tier_far_zero():
    """未检测到脸 (bbox_w=0) 视为 far."""
    tier, scale = compute_tier(bbox_w=0)
    assert tier == "far"
    assert scale == 0.6


def test_tier_custom_thresholds():
    """阈值可注入以便测试和未来调节."""
    tier, scale = compute_tier(bbox_w=50, thresholds=(40, 100), sizes=(2.0, 1.0, 0.5))
    assert tier == "mid"
    assert scale == 1.0
