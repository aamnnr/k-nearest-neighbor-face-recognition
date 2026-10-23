import numpy as np

from liveness import LivenessChecker, eye_aspect_ratio

OPEN_EYE = np.array([(0, 0), (2, -2), (4, -2), (6, 0), (4, 2), (2, 2)])
CLOSED_EYE = np.array([(0, 0), (2, 0), (4, 0), (6, 0), (4, 0), (2, 0)])


def test_eye_aspect_ratio():
    assert eye_aspect_ratio(OPEN_EYE) > 0.5
    assert eye_aspect_ratio(CLOSED_EYE) == 0


def test_blink_requires_close_then_open():
    checker = LivenessChecker(ear_threshold=0.2)
    checker.update_eyes(0.3)
    assert not checker.blinked
    checker.update_eyes(0.1)
    checker.update_eyes(0.3)
    assert checker.blinked


def test_passed_needs_blink_and_smile_and_reset_clears():
    checker = LivenessChecker()
    checker.update_eyes(0.1)
    checker.update_eyes(0.3)
    assert not checker.passed
    checker.mark_smile()
    assert checker.passed
    checker.reset()
    assert not checker.passed
