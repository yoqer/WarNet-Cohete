Acceleration-Based Parachute Triggers
======================================

RocketPy supports advanced parachute deployment logic using acceleration data
from simulated IMU (Inertial Measurement Unit) sensors. This enables realistic
avionics algorithms that mimic real-world flight computers.

Overview
--------

Traditional parachute triggers rely on altitude and velocity. Acceleration-based
triggers provide additional capabilities:

- **Motor burnout detection**: Implement as a custom trigger with mission-specific thresholds
- **Apogee detection**: Use acceleration and velocity together for precise apogee
- **Freefall detection**: Identify ballistic coasting phases
- **Liftoff detection**: Confirm motor ignition via high acceleration

These triggers can optionally include sensor noise to simulate realistic IMU
behavior, making simulations more representative of actual flight conditions.

Built-in Trigger
----------------

RocketPy provides one built-in trigger string:

Apogee Detection
~~~~~~~~~~~~~~~~

Detects apogee when the rocket starts descending.

.. code-block:: python

    main = Parachute(
        name="Main",
        cd_s=10.0,
        trigger="apogee",
        sampling_rate=100,
        lag=0.5
    )

**Detection criteria:**
- Vertical velocity becomes negative (descent starts)

Custom Triggers
---------------

You can create custom triggers that use acceleration data:

Motor Burnout Trigger (Custom Example)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Motor burnout is highly mission-dependent, so it is recommended as a custom
trigger with user-defined thresholds:

.. code-block:: python

    def burnout_trigger_factory(
        min_height=5.0,
        min_vz=0.5,
        az_threshold=-8.0,
        total_acc_threshold=2.0,
    ):
        def burnout_trigger(_pressure, height, state_vector, u_dot):
            if u_dot is None or len(u_dot) < 6:
                return False

            ax, ay, az = u_dot[3], u_dot[4], u_dot[5]
            total_acc = (ax**2 + ay**2 + az**2) ** 0.5
            vz = state_vector[5] if len(state_vector) > 5 else 0

            if height < min_height or vz <= min_vz:
                return False

            return az < az_threshold or total_acc < total_acc_threshold

        return burnout_trigger

    drogue = Parachute(
        name="Drogue",
        cd_s=1.0,
        trigger=burnout_trigger_factory(
            min_height=10.0,
            min_vz=2.0,
            az_threshold=-10.0,
            total_acc_threshold=3.0,
        ),
        sampling_rate=100,
        lag=1.5,
    )

Apogee by Acceleration (Custom Example)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def apogee_acc_trigger(_pressure, _height, state_vector, u_dot):
        vz = state_vector[5]
        az = u_dot[5]
        return abs(vz) < 1.0 and az < -0.1

Free-fall (Custom Example)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def freefall_trigger(_pressure, height, state_vector, u_dot):
        ax, ay, az = u_dot[3], u_dot[4], u_dot[5]
        total_acc = (ax**2 + ay**2 + az**2) ** 0.5
        vz = state_vector[5]
        return height > 5.0 and vz < -0.2 and total_acc < 11.5

Liftoff by Acceleration (Custom Example)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def liftoff_trigger(_pressure, _height, _state_vector, u_dot):
        ax, ay, az = u_dot[3], u_dot[4], u_dot[5]
        total_acc = (ax**2 + ay**2 + az**2) ** 0.5
        return total_acc > 15.0

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

        # Define threshold for IMU reading (example value)
        threshold = 100.0  # Adjust based on sensor units and trigger criteria

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

Sensor Noise
------------

For realistic IMU behavior, use RocketPy sensors with their own noise models.
Parachute trigger functions can receive ``sensors`` and use those measurements
directly instead of injecting noise in the flight solver.

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
4. **Use robust custom logic**: Add mission-specific guards and thresholds
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

    # Drogue parachute: Deploy using a custom burnout trigger
    def drogue_burnout_trigger(_pressure, height, state_vector, u_dot):
        if u_dot is None or len(u_dot) < 6:
            return False
        az = u_dot[5]
        vz = state_vector[5] if len(state_vector) > 5 else 0
        return height > 10 and vz > 1 and az < -8.0

    drogue = Parachute(
        name="Drogue",
        cd_s=1.0,
        trigger=drogue_burnout_trigger,
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

    # Flight simulation
    flight = Flight(
        rocket=my_rocket,
        environment=env,
        rail_length=5.2,
        inclination=85,
        heading=0,
    )

    flight.all_info()

See Also
--------

- :doc:`Parachute Class Reference </reference/rocket/parachute>`
- :doc:`Flight Simulation </user/flight>`
- :doc:`Sensors and Controllers </user/sensors>`
