import os
import shutil
import subprocess
from pathlib import Path
from growth_curves.main import main

def test_growth_curves_smoothing():
    tests_dir = Path(__file__).parent
    data_dir = tests_dir / "data/"
    save_path = tests_dir / 'test_output_hsc/'
    
    if save_path.exists():
        shutil.rmtree(save_path)

    # Construct the CLI command
    command = [
        "growth_curves",
        "-i", os.path.join(data_dir, "HSC_Normals_Biomarkers_FINAL_cleaned.xlsx"),
        "-a", "Age_yrs_",
        "-t", "WM",
        "-b", "Intensity", "Damage_Micro",
        "-d", os.path.join(data_dir, "HSC_Tumour_Biomarkers_FINAL_cleaned.xlsx"),
        "-s", save_path.as_posix(),
        "-sm"
    ]

    # Run the command and capture the result
    result = subprocess.run(command, capture_output=True, text=True)

    # Print command output for debugging
    print(result.stdout)
    print(result.stderr)

    # Assert the command ran successfully
    assert result.returncode == 0
    assert save_path.exists()  # Ensure the output directory is created

def test_growth_curves():
    tests_dir = Path(__file__).parent
    data_dir = tests_dir / "data/"
    save_path = tests_dir / 'test_output_ondri/'
    
    if save_path.exists():
        shutil.rmtree(save_path)

    # Construct the CLI command
    command = [
        "growth_curves",
        "-i", os.path.join(data_dir, "ondri_beam_biomarkers_cleaned.xlsx"),
        "-a", "AGE",
        "-t", "WML",
        "-b", "Volume",
        "-s", save_path.as_posix()
    ]

    # Run the command and capture the result
    result = subprocess.run(command, capture_output=True, text=True)

    # Print command output for debugging
    print(result.stdout)
    print(result.stderr)

    # Assert the command ran successfully
    assert result.returncode == 0
    assert save_path.exists()  # Ensure the output directory is created

