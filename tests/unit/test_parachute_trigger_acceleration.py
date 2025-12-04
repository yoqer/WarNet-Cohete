import numpy as np
import pytest

from rocketpy.simulation.flight import Flight
from rocketpy.rocket.parachute import Parachute


def test_trigger_receives_u_dot_and_noise():
    # Prepare derivative function that returns known u_dot
    def derivative_func(t, y):
        return np.array([0, 0, 0, 1.0, 2.0, 3.0, 0, 0, 0, 0, 0, 0, 0])

    recorded = {}

    # User trigger expecting u_dot named exactly 'u_dot'
    def user_trigger(p, h, y, u_dot):
        recorded["u_dot"] = np.array(u_dot)
        return True

    parachute = Parachute(
        name="test",
        cd_s=1.0,
        trigger=user_trigger,
        sampling_rate=100,
    )

    # Dummy flight-like object with acceleration_noise_function
    dummy = type("D", (), {})()
    dummy.acceleration_noise_function = lambda: np.array([0.1, -0.2, 0.3])

    # Call the helper directly without instantiating full Flight
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
    # Original derivative accelerations were [1.0,2.0,3.0]
    # After noise [0.1,-0.2,0.3] -> [1.1, 1.8, 3.3]
    assert np.allclose(recorded["u_dot"][3:6], np.array([1.1, 1.8, 3.3]))


def test_trigger_with_sensors_and_u_dot():
    def derivative_func(t, y):
        return np.array([0, 0, 0, -1.0, -2.0, -3.0, 0, 0, 0, 0, 0, 0, 0])

    recorded = {}

    def user_trigger(p, h, y, sensors, u_dot):
        recorded["sensors"] = sensors
        recorded["u_dot"] = np.array(u_dot)
        return False

    parachute = Parachute(
        name="test2",
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
        sensors=["s1"],
        derivative_func=derivative_func,
        t=1.234,
    )

    assert res is False
    assert recorded["sensors"] == ["s1"]
    assert np.allclose(recorded["u_dot"][3:6], np.array([-1.0, -2.0, -3.0]))


def test_legacy_trigger_does_not_compute_u_dot():
    # derivative function that raises if called
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

    # Should not raise
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
