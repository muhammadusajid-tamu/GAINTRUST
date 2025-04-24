module load GCCcore/13.3.0
module load Rust/nightly-20250326
module load Python/3.12.3
source GAINTRUST_venv/bin/activate
bash -c 'ollama serve' &
python driver.py