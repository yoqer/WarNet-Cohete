import numpy as np
import traceback

from rocketpy.simulation.flight import Flight
from rocketpy.rocket.parachute import Parachute


def _test_trigger_receives_u_dot_and_noise():
    def derivative_func(t, y):
        return np.array([0, 0, 0, 1.0, 2.0, 3.0, 0, 0, 0, 0, 0, 0, 0])

    recorded = {}

    def user_trigger(p, h, y, u_dot):
        recorded["u_dot"] = np.array(u_dot)
        return True

    parachute = Parachute(
        name="test",
        cd_s=1.0,
        trigger=user_trigger,
        sampling_rate=100,
    )

    dummy = type("D", (), {})()
    dummy.acceleration_noise_function = lambda: np.array([0.1, -0.2, 0.3])

    res = Flight._evaluate_parachute_trigger(
        dummy,
        parachute,
        pressure=0.0,
        height=10.0,
        y=np.zeros(13),
        sensors=[],
        derivative_func=derivative_func,
        t=0.0,
    )

    assert res is True
    assert "u_dot" in recorded
    assert np.allclose(recorded["u_dot"][3:6], np.array([1.1, 1.8, 3.3]))


def _test_trigger_with_u_dot_only():
    """Test trigger that only expects u_dot (no sensors)."""

    def derivative_func(t, y):
        return np.array([0, 0, 0, -1.0, -2.0, -3.0, 0, 0, 0, 0, 0, 0, 0])

    recorded = {}

    def user_trigger(p, h, y, u_dot):
        recorded["u_dot"] = np.array(u_dot)
        return False

    parachute = Parachute(
        name="test_u_dot_only",
        cd_s=1.0,
        trigger=user_trigger,
        sampling_rate=100,
    )

    dummy = type("D", (), {})()
    dummy.acceleration_noise_function = lambda: np.array([0.0, 0.0, 0.0])

    res = Flight._evaluate_parachute_trigger(
        dummy,
        parachute,
        pressure=0.0,
        height=5.0,
        y=np.zeros(13),
        sensors=[],
        derivative_func=derivative_func,
        t=1.234,
    )

    assert res is False
    assert "u_dot" in recorded
    assert np.allclose(recorded["u_dot"][3:6], np.array([-1.0, -2.0, -3.0]))


def _test_legacy_trigger_does_not_compute_u_dot():
    def derivative_func(t, y):
        raise RuntimeError("derivative should not be called for legacy triggers")

    called = {}

    def legacy_trigger(p, h, y):
        called["ok"] = True
        return True

    parachute = Parachute(
        name="legacy",
        cd_s=1.0,
        trigger=legacy_trigger,
        sampling_rate=100,
    )

    dummy = type("D", (), {})()
    dummy.acceleration_noise_function = lambda: np.zeros(3)

    res = Flight._evaluate_parachute_trigger(
        dummy,
        parachute,
        pressure=0.0,
        height=0.0,
        y=np.zeros(13),
        sensors=[],
        derivative_func=derivative_func,
        t=0.0,
    )

    assert res is True
    assert called.get("ok", False) is True


def run_all():
    tests = [
        _test_trigger_receives_u_dot_and_noise,
        _test_trigger_with_u_dot_only,
        _test_legacy_trigger_does_not_compute_u_dot,
    ]
    failures = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[PASS] {name}")
        except Exception:
            failures += 1
            print(f"[FAIL] {name}")
            traceback.print_exc()
    if failures:
        print(f"{failures} test(s) failed")
        raise SystemExit(1)
    print("All tests passed")


if __name__ == "__main__":
    run_all()
