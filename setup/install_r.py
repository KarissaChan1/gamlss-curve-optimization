import subprocess
import platform
import os

def install_r(version="latest"):
    """Install a specific version of R based on the operating system."""
    system = platform.system()
    try:
        if system == "Linux":
            # Install R for Debian/Ubuntu
            print("Detected Linux OS. Installing R...")
            subprocess.run(["sudo", "apt", "update"], check=True)
            if version == "latest":
                subprocess.run(["sudo", "apt", "install", "-y", "r-base"], check=True)
            else:
                # Install a specific version
                r_version_pkg = f"r-base={version}*"
                subprocess.run(["sudo", "apt", "install", "-y", r_version_pkg], check=True)

        elif system == "Darwin":
            # Install R for macOS using Homebrew
            print("Detected macOS. Installing R via Homebrew...")
            if version == "latest":
                subprocess.run(["brew", "install", "r"], check=True)
            else:
                # Install a specific version
                subprocess.run(["brew", "install", f"r@{version}"], check=True)

        elif system == "Windows":
            # Install R for Windows
            print("Detected Windows OS. Downloading and Installing R...")
            base_url = "https://cran.r-project.org/bin/windows/base/"
            installer_filename = f"R-{version}-win.exe" if version != "latest" else "R-latest-win.exe"
            installer_url = base_url + installer_filename
            installer_path = "R_installer.exe"

            # Download the installer
            subprocess.run(["curl", "-o", installer_path, installer_url], check=True)

            # Run the installer silently
            subprocess.run([installer_path, "/SILENT"], check=True)
        else:
            raise RuntimeError("Unsupported Operating System")
    except subprocess.CalledProcessError as e:
        print(f"Error during R installation: {e}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def check_r_installed(required_version=None):
    """Check if R is installed and optionally verify the version."""
    try:
        result = subprocess.run(["R", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        print("R is installed.")
        version_output = result.stdout.split("\n")[0]  # Get the first line of the version output
        print(version_output)

        if required_version:
            # Extract the version number from the output
            import re
            version_match = re.search(r"R version (\d+\.\d+\.\d+)", version_output)
            if version_match:
                installed_version = version_match.group(1)
                if installed_version == required_version:
                    print(f"R version {installed_version} matches the required version.")
                    return True
                else:
                    print(f"Installed R version {installed_version} does not match required version {required_version}.")
                    return False
            else:
                print("Unable to parse the installed R version.")
                return False
        return True
    except FileNotFoundError:
        print("R is not installed.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error checking R installation: {e}")
        return False

def set_environment_variables():
    """Set environment variables for R."""
    try:
        r_home = subprocess.check_output(["R", "RHOME"], text=True).strip()
        os.environ["R_HOME"] = r_home
        print(f"R_HOME set to: {r_home}")
    except subprocess.CalledProcessError as e:
        print(f"Error setting R_HOME: {e}")
        raise

def install_r_packages(packages):
    """Install required R packages."""
    for package in packages:
        print(f"Installing R package: {package}")
        subprocess.run(
            ["R", "-e", f"if (!require('{package}', quietly = TRUE)) install.packages('{package}', repos='http://cran.r-project.org')"],
            check=True
        )

# Main logic
if __name__ == "__main__":
    # Check if R is installed
    r_version = "4.4.2"
    if not check_r_installed(required_version=r_version):
        install_r(version=r_version)
        if not check_r_installed(required_version=r_version):
            raise RuntimeError("Failed to install R.")

    # Set R environment variables
    set_environment_variables()

    # Install required R packages
    required_packages = ["ggplot2", "gamlss", "dplyr"]
    install_r_packages(required_packages)