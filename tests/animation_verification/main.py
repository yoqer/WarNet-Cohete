import os
import traceback
from rocketpy import Environment, Flight
from rocket_stl import create_rocket_stl
from rocket_setup import get_calisto_rocket


def run_simulation_and_test_animation():
    print("🚀 Setting up simulation (Calisto Example)...")

    # 1. Setup Environment
    env = Environment(latitude=32.990254, longitude=-106.974998, elevation=1400)
    env.set_date((2025, 12, 5, 12))
    env.set_atmospheric_model(type="standard_atmosphere")

    # 2. Get Rocket
    try:
        calisto = get_calisto_rocket()
    except Exception as e:
        print(f"❌ Failed to configure rocket: {e}")
        return

    # 3. Simulate Flight
    test_flight = Flight(
        rocket=calisto, environment=env, rail_length=5.2, inclination=85, heading=0
    )

    print(f"✅ Flight simulated successfully! Apogee: {test_flight.apogee:.2f} m")

    # 4. Test Animation Methods
    stl_file = "rocket_model.stl"
    # Note: Depending on where you run this, you might need to adjust imports
    # or ensure create_rocket_stl is available in scope.
    create_rocket_stl(stl_file, length=300, radius=50)

    print("\n🎥 Testing animate_trajectory()...")

    try:
        test_flight.animate_trajectory(
            file_name=stl_file,
            stop=15.0,
            time_step=0.05,
            azimuth=-45,  # Rotates view 45 degrees left
            elevation=30,  # Tilts view 30 degrees up
            zoom=1.2,
        )
        print("✅ animate_trajectory() executed successfully.")
    except Exception as e:
        print(f"❌ animate_trajectory() Failed: {e}")
        traceback.print_exc()

    print("\n🔄 Testing animate_rotate()...")

    try:
        test_flight.animate_rotate(
            file_name=stl_file,
            time_step=1.0,
            azimuth=-45,  # Rotates view 45 degrees left
            elevation=30,  # Tilts view 30 degrees up
            zoom=1.2,
        )
        print("✅ animate_rotate() executed successfully.")
    except Exception as e:
        print(f"❌ animate_rotate() Failed: {e}")
        traceback.print_exc()

    # Cleanup
    if os.path.exists(stl_file):
        os.remove(stl_file)


if __name__ == "__main__":
    run_simulation_and_test_animation()
