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

    query_engine = QueryEngineFactory.create_engine("local", global_constraints)

    response = query_engine.query(f"You are given C code contained in <code> tags."
                + " We need to translate this code to Rust.\n\n"
                + "<code> #include <iostream> int main(){ std::cout << \"Hello World\" << std::endl return 0 } <code>"
                + "Give me Rust refactoring of above {self.src_lang.capitalize()} code. "
                + "Use the same function name, same argument and return types. "
                + "Make sure it includes all imports, uses safe rust, and compiles. "
                + "Don't use raw pointers. "
                + "Use box pointer whenever possible. Box pointers are preferable to other alternatives. "
                + "Try not to use Traits if possible. I would not like to have Traits in resulting Rust code. "
                + "Try not to use Generics if possible.")
    print(response)


if __name__ == "__main__":
    main()
