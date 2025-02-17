from settings import Options
from argparse_dataclass import ArgumentParser
from llms import QueryEngineFactory
from transformers import pipeline

def main():

    print("Testing...")
    parser = ArgumentParser(Options)
    options = parser.parse_args()   
    # messages = [
    #     {"role": "user", "content": "Who are you?"},
    # ]
    # #pipe = pipeline("text-generation", model="Qwen/Qwen2.5-Coder-32B-Instruct")
    # pipe = pipeline("text-generation", model="Qwen/Qwen2.5-0.5B-Instruct")
    # print(pipe(messages))

    global_constraints = []
    if options.language == "c":
        global_constraints.append("Consider using functions like `wrapping_add` to simulate C semantics.")

    if options.language == "go" and options.benchmark_name != "ach":
        global_constraints.append("If possible, use free standing functions instead of associated methods/functions.")

    if options.benchmark_name == "triangolatte":
        global_constraints.append("Unless necessary, don't generate `new` method for structs.")

    if options.benchmark_name == "go-edlib":
       global_constraints.append("Note that `int` in Golang is platform dependent, which should be mapped to `isize` in Rust.")

    print(options.model)

    c_code = """#include <iostream> 
    int main() { 
        std::cout << "Hello World" << std::endl; 
        return 0; 
    }"""

    prompt = (
        "You are given C code inside <code> tags. "
        "Translate this C code into Rust while keeping the function name, arguments, and return types the same.\n\n"
        f"<code> {c_code} </code>\n\n"
        "Requirements:\n"
        "- Ensure the Rust code compiles and includes all necessary imports.\n"
        "- Use safe Rust, avoiding raw pointers.\n"
        "- Prefer `Box` pointers when applicable.\n"
        "- Avoid using Traits and Generics whenever possible.\n"
        "Now, provide the translated Rust code:"
    )
    query_engine = QueryEngineFactory.create_engine(options.model, global_constraints)

    response = query_engine.query(prompt)
    print(response)


if __name__ == "__main__":
    main()
