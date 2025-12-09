Acceleration-Based Parachute Triggers
======================================

RocketPy supports advanced parachute deployment logic using acceleration data
from simulated IMU (Inertial Measurement Unit) sensors. This enables realistic
avionics algorithms that mimic real-world flight computers.

Overview
--------

Traditional parachute triggers rely on altitude and velocity. Acceleration-based
triggers provide additional capabilities:

- **Motor burnout detection**: Detect thrust termination via sudden deceleration
- **Apogee detection**: Use acceleration and velocity together for precise apogee
- **Freefall detection**: Identify ballistic coasting phases
- **Liftoff detection**: Confirm motor ignition via high acceleration

These triggers can optionally include sensor noise to simulate realistic IMU
behavior, making simulations more representative of actual flight conditions.

Built-in Triggers
-----------------

RocketPy provides four built-in acceleration-based triggers:

Motor Burnout Detection
~~~~~~~~~~~~~~~~~~~~~~~~

Detects when the motor stops producing thrust by monitoring sudden drops in
acceleration magnitude.

.. code-block:: python

    from rocketpy import Parachute

    drogue = Parachute(
        name="Drogue",
        cd_s=1.0,
        trigger="burnout",  # Built-in trigger
        sampling_rate=100,
        lag=1.5
    )

**Detection criteria:**
- Vertical acceleration < -8.0 m/s² (end of thrust phase), OR
- Total acceleration magnitude < 2.0 m/s² (coasting detected)
- Rocket must be above 5m altitude and ascending (prevents false triggers at launch)

Apogee Detection
~~~~~~~~~~~~~~~~

Detects apogee using both near-zero vertical velocity and negative vertical
acceleration.

.. code-block:: python

    main = Parachute(
        name="Main",
        cd_s=10.0,
        trigger="apogee_acc",  # Acceleration-based apogee
        sampling_rate=100,
        lag=0.5
    )

**Detection criteria:**
- Absolute vertical velocity < 1.0 m/s
- Vertical acceleration < -0.1 m/s² (downward)

Freefall Detection
~~~~~~~~~~~~~~~~~~

Detects free-fall by monitoring very low total acceleration (near gravitational
acceleration only).

.. code-block:: python

    drogue = Parachute(
        name="Drogue",
        cd_s=1.0,
        trigger="freefall",
        sampling_rate=100,
        lag=1.0
    )

**Detection criteria:**
- Total acceleration magnitude < 11.5 m/s²
- Rocket descending (vz < -0.2 m/s)
- Altitude > 5m (prevents ground-level false triggers)

Liftoff Detection
~~~~~~~~~~~~~~~~~

Detects motor ignition via high total acceleration.

.. code-block:: python

    test_parachute = Parachute(
        name="Test",
        cd_s=0.5,
        trigger="liftoff",
        sampling_rate=100,
        lag=0.0
    )

**Detection criteria:**
- Total acceleration magnitude > 15.0 m/s²

Custom Triggers
---------------

You can create custom triggers that use acceleration data:

.. code-block:: python

    def custom_trigger(pressure, height, state_vector, u_dot):
        """
        Custom trigger using acceleration data.

        Parameters
        ----------
        pressure : float
            Atmospheric pressure in Pa (with optional noise)
        height : float
            Height above ground level in meters (with optional noise)
        state_vector : array
            [x, y, z, vx, vy, vz, e0, e1, e2, e3, wx, wy, wz]
        u_dot : array
            Derivative: [vx, vy, vz, ax, ay, az, e0_dot, ...]
            Accelerations are at indices [3:6]

        Returns
        -------
        bool
            True to trigger parachute deployment
        """
        # Extract acceleration components (m/s²)
        ax = u_dot[3]
        ay = u_dot[4]
        az = u_dot[5]

        # Calculate total acceleration magnitude
        total_acc = (ax**2 + ay**2 + az**2)**0.5

        # Custom logic: deploy if total acceleration < 5 m/s² while descending
        vz = state_vector[5]
        return total_acc < 5.0 and vz < -10.0

    # Use custom trigger
    parachute = Parachute(
        name="Custom",
        cd_s=2.0,
        trigger=custom_trigger,
        sampling_rate=100,
        lag=1.0
    )

Sensor and Acceleration Triggers
---------------------------------

Triggers can also accept sensor data alongside acceleration:

.. code-block:: python

    def advanced_trigger(pressure, height, state_vector, sensors, u_dot):
        """
        Advanced trigger using both sensors and acceleration.

        Parameters
        ----------
        sensors : list
            List of sensor objects attached to the rocket
        u_dot : array
            State derivative including accelerations

        Returns
        -------
        bool
        """
        # Access sensor measurements
        if len(sensors) > 0:
            imu_reading = sensors[0].measurement

        # Use acceleration data
        az = u_dot[5]

        # Combine sensor and acceleration logic
        return az < -5.0 and imu_reading > threshold

    parachute = Parachute(
        name="Advanced",
        cd_s=1.5,
        trigger=advanced_trigger,
        sampling_rate=100
    )

Adding Acceleration Noise
--------------------------

To simulate realistic IMU behavior, you can add noise to acceleration data:

.. code-block:: python

    from rocketpy import Flight

    flight = Flight(
        rocket=my_rocket,
        environment=env,
        rail_length=5.2,
        inclination=85,
        heading=0,
        acceleration_noise_function=lambda: np.random.normal(0, 0.5, 3)
    )

The ``acceleration_noise_function`` returns a 3-element array ``[noise_x, noise_y, noise_z]``
that is added to the acceleration components before passing to the trigger function.

**Example with time-correlated noise:**

.. code-block:: python

    class NoiseGenerator:
        def __init__(self, stddev=0.5, correlation=0.9):
            self.stddev = stddev
            self.correlation = correlation
            self.last_noise = np.zeros(3)

        def __call__(self):
            # Time-correlated noise (AR(1) process)
            white_noise = np.random.normal(0, self.stddev, 3)
            self.last_noise = (self.correlation * self.last_noise +
                               np.sqrt(1 - self.correlation**2) * white_noise)
            return self.last_noise

    flight = Flight(
        rocket=my_rocket,
        environment=env,
        rail_length=5.2,
        inclination=85,
        heading=0,
        acceleration_noise_function=NoiseGenerator(stddev=0.3, correlation=0.95)
    )

Performance Considerations
--------------------------

Computing acceleration (``u_dot``) requires evaluating the equations of motion,
which adds computational cost. RocketPy optimizes this by:

1. **Lazy evaluation**: ``u_dot`` is only computed if the trigger actually needs it
2. **Metadata detection**: The wrapper inspects trigger signatures to determine requirements
3. **Caching**: Derivative evaluations are reused when possible

**Trigger signature detection:**

- 3 parameters ``(p, h, y)``: Legacy trigger, no ``u_dot`` computed
- 4 parameters with ``u_dot``: Only acceleration computed
- 4 parameters with ``sensors``: Only sensors passed
- 5 parameters: Both sensors and acceleration provided

Best Practices
--------------

1. **Choose appropriate sampling rates**: 50-200 Hz is typical for flight computers
2. **Add realistic noise**: Real IMUs have noise; simulate it for validation
3. **Test edge cases**: Verify triggers work at low altitudes, high speeds, etc.
4. **Use built-in triggers**: They handle edge cases (NaN, Inf) automatically
5. **Document custom triggers**: Include detection criteria in docstrings

Example: Complete Dual-Deploy System
-------------------------------------

.. code-block:: python

    from rocketpy import Rocket, Parachute, Flight, Environment
    import numpy as np

    # Environment and rocket setup
    env = Environment(latitude=32.99, longitude=-106.97, elevation=1400)
    env.set_atmospheric_model(type="standard_atmosphere")

    my_rocket = Rocket(...)  # Define your rocket

    # Drogue parachute: Deploy at motor burnout
    drogue = Parachute(
        name="Drogue",
        cd_s=1.0,
        trigger="burnout",
        sampling_rate=100,
        lag=1.5,
        noise=(0, 8.3, 0.5)  # Pressure sensor noise
    )
    my_rocket.add_parachute(drogue)

    # Main parachute: Deploy at 800m using custom trigger
    def main_deploy_trigger(pressure, height, state_vector, u_dot):
        """Deploy main at 800m while descending with positive vertical acceleration."""
        vz = state_vector[5]
        az = u_dot[5]
        return height < 800 and vz < -5 and az > -15

    main = Parachute(
        name="Main",
        cd_s=10.0,
        trigger=main_deploy_trigger,
        sampling_rate=100,
        lag=0.5,
        noise=(0, 8.3, 0.5)
    )
    my_rocket.add_parachute(main)

    # Flight with IMU noise simulation
    flight = Flight(
        rocket=my_rocket,
        environment=env,
        rail_length=5.2,
        inclination=85,
        heading=0,
        acceleration_noise_function=lambda: np.random.normal(0, 0.3, 3)
    )

    flight.all_info()

See Also
--------

- :doc:`Parachute Class Reference </reference/rocket/parachute>`
- :doc:`Flight Simulation </user/flight>`
- :doc:`Sensors and Controllers </user/sensors>`
