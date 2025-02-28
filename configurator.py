import json
from settings import Options
from dataclasses import asdict

class Config:
    @staticmethod
    def from_json_file(file_path: str) -> Options:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return Options(**{**asdict(Options(benchmark_name = "libopenaptx/aptx_bin_search", submodule_name = "aptx_bin_search", tag ="test")), **data})
        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading options: {e}")
            return Options()

    @staticmethod
    def to_json_file(file_path: str, options: Options):
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(options.__dict__, file, indent=4)
        except IOError as e:
            print(f"Error saving options: {e}")