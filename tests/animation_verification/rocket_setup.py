import os
from rocketpy import SolidMotor, Rocket

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
DATA_DIR = os.path.join(ROOT_DIR, "data")

OFF_DRAG_PATH = os.path.join(DATA_DIR, "rockets/calisto/powerOffDragCurve.csv")
ON_DRAG_PATH = os.path.join(DATA_DIR, "rockets/calisto/powerOnDragCurve.csv")
AIRFOIL_PATH = os.path.join(DATA_DIR, "airfoils/NACA0012-radians.txt")
MOTOR_PATH = os.path.join(DATA_DIR, "motors/cesaroni/Cesaroni_M1670.eng")


def get_motor():
    """Locates the motor file and returns a configured SolidMotor object."""
    # We can now point directly to the file without searching
    if not os.path.exists(MOTOR_PATH):
        raise FileNotFoundError(f"Could not find Cesaroni_M1670.eng at: {MOTOR_PATH}")

    return SolidMotor(
        thrust_source=MOTOR_PATH,
        dry_mass=1.815,
        dry_inertia=(0.125, 0.125, 0.002),
        nozzle_radius=33 / 1000,
        grain_number=5,
        grain_density=1815,
        grain_outer_radius=33 / 1000,
        grain_initial_inner_radius=15 / 1000,
        grain_initial_height=120 / 1000,
        grain_separation=5 / 1000,
        grains_center_of_mass_position=0.397,
        center_of_dry_mass_position=0.317,
        nozzle_position=0,
        burn_time=3.9,
        throat_radius=11 / 1000,
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )


def get_calisto_rocket():
    """Configures and returns the Calisto Rocket object."""
    motor = get_motor()

    calisto = Rocket(
        radius=127 / 2000,
        mass=14.426,
        inertia=(6.321, 6.321, 0.034),
        power_off_drag=OFF_DRAG_PATH,
        power_on_drag=ON_DRAG_PATH,
        center_of_mass_without_motor=0,
        coordinate_system_orientation="tail_to_nose",
    )

    calisto.add_motor(motor, position=-1.255)
    calisto.set_rail_buttons(
        upper_button_position=0.0818,
        lower_button_position=-0.618,
        angular_position=45,
    )

    # Aerodynamic surfaces
    calisto.add_nose(length=0.55829, kind="vonKarman", position=1.27)
    calisto.add_trapezoidal_fins(
        n=4,
        root_chord=0.120,
        tip_chord=0.060,
        span=0.110,
        position=-1.04956,
        cant_angle=0,
        airfoil=(AIRFOIL_PATH, "radians"),
    )
    calisto.add_tail(
        top_radius=0.0635, bottom_radius=0.0435, length=0.060, position=-1.194656
    )

    # Parachutes
    calisto.add_parachute(
        name="Main",
        cd_s=10.0,
        trigger=800,
        sampling_rate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )
    calisto.add_parachute(
        name="Drogue",
        cd_s=1.0,
        trigger="apogee",
        sampling_rate=105,
        lag=1.5,
        noise=(0, 8.3, 0.5),
    )

    return calisto
