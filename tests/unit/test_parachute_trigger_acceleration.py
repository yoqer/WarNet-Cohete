"""Unit tests for acceleration-based parachute triggers.

Tests cover trigger function signatures, noise injection, built-in triggers,
and edge cases for realistic avionics simulation.
"""

import numpy as np
import pytest

from rocketpy.rocket.parachute import (
    Parachute,
    detect_apogee_acceleration,
    detect_freefall,
    detect_liftoff,
    detect_motor_burnout,
)
from rocketpy.simulation.flight import Flight


class TestTriggerSignatures:
    """Test various trigger function signatures and detection."""

    def test_trigger_receives_u_dot_and_noise(self):
        """Test that triggers receive u_dot with injected noise.

        Verifies acceleration data is computed and noise is injected before
        passing to user trigger functions.
        """

        # Arrange
        def derivative_func(_t, _y):
            return np.array([0, 0, 0, 1.0, 2.0, 3.0, 0, 0, 0, 0, 0, 0, 0])

        recorded = {}

        def user_trigger(_p, _h, _y, u_dot):
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

        # Act
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

        # Assert
        assert res is True
        assert "u_dot" in recorded
        assert np.allclose(recorded["u_dot"][3:6], np.array([1.1, 1.8, 3.3]))

    def test_trigger_with_sensors_and_u_dot(self):
        """Test trigger with both sensors and u_dot parameters.

        Verifies wrapper correctly passes both sensors and acceleration data
        to triggers expecting 5 parameters.
        """

        # Arrange
        def derivative_func(_t, _y):
            return np.array([0, 0, 0, -1.0, -2.0, -3.0, 0, 0, 0, 0, 0, 0, 0])

        recorded = {}

        def user_trigger(_p, _h, _y, sensors, u_dot):
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

        # Act
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

        # Assert
        assert res is False
        assert recorded["sensors"] == ["s1"]
        assert np.allclose(recorded["u_dot"][3:6], np.array([-1.0, -2.0, -3.0]))

    def test_legacy_trigger_does_not_compute_u_dot(self):
        """Test that legacy 3-parameter triggers don't trigger u_dot computation.

        Ensures backward compatibility by skipping expensive derivative
        computation when not needed.
        """

        # Arrange
        def derivative_func(_t, _y):
            raise RuntimeError("derivative should not be called for legacy triggers")

        called = {}

        def legacy_trigger(_p, _h, _y):
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

        # Act & Assert
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


class TestBuiltInTriggers:
    """Test built-in acceleration-based trigger functions."""

    def test_detect_apogee_acceleration_at_peak(self):
        """Test apogee detection when velocity is near zero with negative acceleration.

        Apogee detection requires vertical velocity close to zero and
        downward acceleration (negative az).
        """
        # Arrange
        state_vector = [0, 0, 1000, 0, 0, 0.3, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, -1.0, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_apogee_acceleration(101325, 1000, state_vector, u_dot)

        # Assert
        assert bool(result) is True

    def test_detect_apogee_acceleration_ascending(self):
        """Test apogee detection returns False while still ascending.

        Rocket must have near-zero vertical velocity to trigger apogee.
        """
        # Arrange
        state_vector = [0, 0, 500, 0, 0, 50, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, -9.8, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_apogee_acceleration(101325, 500, state_vector, u_dot)

        # Assert
        assert bool(result) is False

    def test_detect_motor_burnout_high_deceleration(self):
        """Test burnout detection with sudden high negative acceleration.

        Motor burnout is indicated by total acceleration magnitude dropping
        significantly.
        """
        # Arrange
        state_vector = [0, 0, 200, 0, 0, 100, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, -12.0, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_motor_burnout(101325, 200, state_vector, u_dot)

        # Assert
        assert bool(result) is True

    def test_detect_motor_burnout_low_total_acceleration(self):
        """Test burnout detection when total acceleration falls below threshold.

        Low total acceleration (< 1.5 m/s²) with descending rocket indicates
        motor burnout.
        """
        # Arrange
        state_vector = [0, 0, 200, 0, 0, 100, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0.5, 0.5, 0.5, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_motor_burnout(101325, 200, state_vector, u_dot)

        # Assert
        assert bool(result) is True

    def test_detect_freefall_near_zero_acceleration(self):
        """Test freefall detection with near-zero total acceleration.

        Freefall occurs when total acceleration is very small (sensor noise level).
        """
        # Arrange
        state_vector = [0, 0, 500, 0, 0, -20, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0.1, 0.1, 0.1, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_freefall(101325, 500, state_vector, u_dot)

        # Assert
        assert bool(result) is True

    def test_detect_liftoff_high_acceleration(self):
        """Test liftoff detection with high upward acceleration.

        Liftoff requires total acceleration > 15 m/s² and low altitude.
        """
        # Arrange
        state_vector = [0, 0, 2, 0, 0, 5, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, 20.0, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_liftoff(101325, 2, state_vector, u_dot)

        # Assert
        assert bool(result) is True

    def test_detect_liftoff_on_pad(self):
        """Test liftoff detection returns False while on launch pad.

        No liftoff until acceleration threshold is exceeded.
        """
        # Arrange
        state_vector = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result = detect_liftoff(101325, 0, state_vector, u_dot)

        # Assert
        assert bool(result) is False


class TestParachuteInitialization:
    """Test parachute creation with different trigger types."""

    def test_parachute_string_trigger_apogee_acc(self):
        """Test parachute initialization with 'apogee' string trigger."""
        # Arrange & Act
        parachute = Parachute(
            name="Main",
            cd_s=1.5,
            trigger="apogee_acc",
            sampling_rate=105,
        )

        # Assert
        assert parachute.triggerfunc is not None
        assert hasattr(parachute.triggerfunc, "_expects_udot")
        assert bool(parachute.triggerfunc._expects_udot) is True

    def test_parachute_string_trigger_burnout(self):
        """Test parachute initialization with 'burnout' string trigger."""
        # Arrange & Act
        parachute = Parachute(
            name="Drogue",
            cd_s=0.5,
            trigger="burnout",
            sampling_rate=100,
        )

        # Assert
        assert parachute.triggerfunc is not None
        assert hasattr(parachute.triggerfunc, "_expects_udot")
        assert bool(parachute.triggerfunc._expects_udot) is True

    def test_parachute_numeric_altitude_trigger(self):
        """Test parachute with numeric altitude-based trigger.

        Altitude triggers do not require u_dot computation for performance.
        """
        # Arrange & Act
        parachute = Parachute(
            name="Main",
            cd_s=1.5,
            trigger=500,
            sampling_rate=105,
        )

        # Assert
        assert parachute.triggerfunc is not None
        assert hasattr(parachute.triggerfunc, "_expects_udot")
        assert bool(parachute.triggerfunc._expects_udot) is False

    def test_parachute_callable_trigger_5_args(self):
        """Test parachute with custom trigger expecting sensors and u_dot."""

        # Arrange
        def custom_trigger(_p, _h, _y, sensors, u_dot):
            return len(sensors) > 0 and u_dot[5] < -5.0

        # Act
        parachute = Parachute(
            name="Custom",
            cd_s=1.0,
            trigger=custom_trigger,
            sampling_rate=100,
        )

        # Assert
        assert parachute.triggerfunc is not None
        assert hasattr(parachute.triggerfunc, "_expects_udot")
        assert hasattr(parachute.triggerfunc, "_expects_sensors")

    def test_parachute_invalid_string_trigger(self):
        """Test parachute initialization raises ValueError for invalid trigger string."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Unable to set the trigger function"):
            Parachute(
                name="Invalid",
                cd_s=1.0,
                trigger="invalid_trigger_name",
                sampling_rate=100,
            )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_trigger_with_nan_values(self):
        """Test that triggers handle NaN values gracefully.

        Triggers should return False (safe default) when data is invalid.
        """
        # Arrange
        state_vector = [0, 0, 500, 0, 0, float("nan"), 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, float("nan"), 0, 0, 0, 0, 0, 0, 0]

        # Act
        result_apogee = detect_apogee_acceleration(101325, 500, state_vector, u_dot)
        result_burnout = detect_motor_burnout(101325, 500, state_vector, u_dot)
        result_freefall = detect_freefall(101325, 500, state_vector, u_dot)
        result_liftoff = detect_liftoff(101325, 500, state_vector, u_dot)

        # Assert
        assert bool(result_apogee) is False
        assert bool(result_burnout) is False
        assert bool(result_freefall) is False
        assert bool(result_liftoff) is False

    def test_trigger_with_inf_values(self):
        """Test that triggers handle infinity values safely."""
        # Arrange
        state_vector = [0, 0, 500, 0, 0, float("inf"), 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, float("inf"), 0, 0, 0, 0, 0, 0, 0]

        # Act & Assert - should not raise, just return False
        result_apogee = detect_apogee_acceleration(101325, 500, state_vector, u_dot)
        result_freefall = detect_freefall(101325, 500, state_vector, u_dot)

        assert bool(result_apogee) is False
        assert bool(result_freefall) is False

    def test_trigger_at_very_low_altitude(self):
        """Test triggers near ground level (edge case).

        Some triggers have altitude thresholds to prevent false positives.
        """
        # Arrange
        state_vector = [0, 0, 1, 0, 0, -5, 1, 0, 0, 0, 0, 0, 0]
        u_dot = [0, 0, 0, 0, 0, -0.5, 0, 0, 0, 0, 0, 0, 0]

        # Act
        result_burnout = detect_motor_burnout(101325, 1, state_vector, u_dot)
        result_freefall = detect_freefall(101325, 1, state_vector, u_dot)

        # Assert - should not trigger at very low altitude
        assert bool(result_burnout) is False
        assert bool(result_freefall) is False

    def test_trigger_with_no_noise_function(self):
        """Test trigger evaluation when acceleration_noise_function is None."""

        # Arrange
        def derivative_func(_t, _y):
            return np.array([0, 0, 0, 1.0, 2.0, 3.0, 0, 0, 0, 0, 0, 0, 0])

        recorded = {}

        def user_trigger(_p, _h, _y, u_dot):
            recorded["u_dot"] = np.array(u_dot)
            return False

        parachute = Parachute(
            name="test",
            cd_s=1.0,
            trigger=user_trigger,
            sampling_rate=100,
        )

        dummy = type("D", (), {})()
        dummy.acceleration_noise_function = None  # No noise

        # Act
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

        # Assert
        assert res is False
        assert "u_dot" in recorded
        assert np.allclose(recorded["u_dot"][3:6], np.array([1.0, 2.0, 3.0]))

    def test_trigger_derivative_computation_error(self):
        """Test trigger evaluation handles derivative computation errors gracefully."""

        # Arrange
        def derivative_func(_t, _y):
            raise ValueError("Derivative computation failed")

        recorded = {}

        def user_trigger(_p, _h, _y, u_dot):
            recorded["called"] = True
            recorded["u_dot"] = u_dot
            return False

        parachute = Parachute(
            name="test",
            cd_s=1.0,
            trigger=user_trigger,
            sampling_rate=100,
        )

        dummy = type("D", (), {})()
        dummy.acceleration_noise_function = None

        # Act - should not raise, fallback gracefully
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

        # Assert - function should still be called with None u_dot (fallback)
        assert res is False
        assert recorded.get("called", False) is True
