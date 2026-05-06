import os
import sys
import subprocess
import urllib.request

def main(argv):

    envname = 'bio334_env'

    i = 1
    while i < len(argv):
        if ((argv[i] == "-e") or (argv[i] == "--envname")):
            envname = str(argv[i+1])
            i += 2
        else:
            raise IOError ("Unrecognized option:", argv[i])
    create_virtual_env(envname)

def run_command(command, shell=False):
    """Run a shell command and handle errors"""
    try:
        subprocess.run(command, shell=shell, check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Failed to run command: {' '.join(command)}")
        sys.exit(1)

def install_python3_venv():
    """Install python3-venv if not found"""
    try:
        subprocess.run([sys.executable, "-m", "venv", "--help"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Installing python3-venv...")
        if not sys.platform.startswith("win"):
            try:
                ## venv the preferred environment tool
                run_command(["sudo", "apt", "install", "-y", "python3-venv"])
            except:
                run_command(["pip", "install", "virtualenv"])
        else:
            run_command(["pip", "install", "virtualenv"])

def download_and_install_pip(python_bin):
    """If pip is missing, download and install it using get-pip.py"""
    print("Downloading get-pip.py to install pip...")
    url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = os.path.join(os.getcwd(), "get-pip.py")
    try:
        urllib.request.urlretrieve(url, get_pip_path)
    except:
        raise RuntimeError ('Failed to retrieve URL. Please check your internet connection')
    print("Installing pip...")
    run_command([python_bin, "-m", "pip", "install", get_pip_path])
    os.remove(get_pip_path)

def check_install_pip(python_bin, pip_bin):
    try:
        run_command([python_bin, "-m", "pip", "--version"])
    except:
        download_and_install_pip(python_bin)

    ## Upgrade pip to the latest version
    print("Upgrading pip...")
    try:
        run_command([pip_bin, "install", "--upgrade", "pip"])
    except:
        run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

def create_virtual_env(env_name):
    """Create a virtual environment and install COBRApy."""

    install_python3_venv()

    if not os.path.exists(env_name):
        print(f"Creating virtual environment: {env_name}...")
        try:
            run_command([sys.executable, "-m", "venv", env_name])
        except:
            run_command(["virtualenv", env_name])
        print(f"Virtual environment created at: {os.path.abspath(env_name)}")

    ## Determine paths inside the virtual environment
    python_bin = os.path.join(env_name, "Scripts", "python") if sys.platform == "win32" else os.path.join(env_name, "bin", "python")
    pip_bin = os.path.join(env_name, "Scripts", "pip") if sys.platform == "win32" else os.path.join(env_name, "bin", "pip")

    ## Ensure that pip is installed in the virtual environment
    print("Checking if pip is available...")
    try:
        check_install_pip(python_bin, pip_bin)
    except:
        raise OSError ('pip installation failed. Please follow the instructions in INSTALL.md to manually install pip')

    ## Install python packages with pip
    for pckg_name in ['jupyterlab', 'cobra']:
        print(f'Installing {pckg_name}')
        try:
            run_command([pip_bin, "install", pckg_name])
        except:
            print(f'{pckg_name} installation failed')
            if pckg_name == 'cobra' and sys.version_info < (3, 8):
                print(f"COBRApy requires Python 3.8+. Your version is \
                    {sys.version.split(' (')[0]}. Please download a newer version at {https://www.python.org/downloads/}")
            sys.exit(1)

    ## Determine activation script
    activate_script = os.path.join(env_name, "Scripts", "activate") if sys.platform == "win32" else os.path.join(env_name, "bin", "activate")

    print("\n --- Installation complete ---")
    print(f"To activate the virtual environment, run:\n source {activate_script} (on macOS/Linux)\n {activate_script}  (on Windows)")

if __name__ == "__main__":
    main(sys.argv)
