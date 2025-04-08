#!/bin/bash

# Update system and install virtual environment package
sudo apt update && sudo apt install python3-venv -y

# Install Rust and required dependencies
sudo apt install rustup -y
sudo apt install cargo -y
sudo apt install build-essential llvm clang libclang-dev cmake libssl-dev pkg-config python3 git -y
rustup default nightly
cargo install c2rust
# Create and activate virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Define an array of required Python libraries
packages=(
    numpy
    tenacity
    transformers
    argparse-dataclass
    anthropic
    boto3
    openai
    google-generativeai
    overrides
    matplotlib
    accelerate
)

# Loop through the array and install each package
for package in "${packages[@]}"; do
    echo -e "\e[1;34msetup.sh:\e[0m\e[33m Installing $package...\e[0m"
    pip install "$package"
    echo -e "\e[1;34msetup.sh:\e[0m\e[32m Finished installing $package.\e[0m\n"
done

# setup should be complete, prompt user to manually start virtual environment
echo "------------------------------------------------"
echo "Virtual environment setup is complete!"
echo "To activate the virtual environment, run:"
echo ""
echo -e "    \e[33msource myenv/bin/activate\e[0m"
echo ""
echo "------------------------------------------------"
