import re
import os
import sys
import shutil
import subprocess

def extract_functions(c_file):
    with open(c_file, 'r', encoding='utf-8') as file:
        code = file.read()

    function_pattern = re.compile(
        r'^(?!\s*(?:if|else\s+if|else|while|for|switch|do|return)\b)\s*\w+[\w\s\*]*\s+(\w+)\s*\([\s\S]*?\)\s*\{',
        re.MULTILINE
    )

    functions = []
    stack = 0
    start_index = None

    for match in function_pattern.finditer(code):
        if start_index is not None:
            continue  # Skip if we're already inside a function

        start_index = match.start()
        stack = 1  # We're inside a function

        for i in range(match.end(), len(code)):
            if code[i] == '{':
                stack += 1
            elif code[i] == '}':
                stack -= 1
                if stack == 0:  # Function end
                    functions.append((match.group(1), code[start_index:i+1]))
                    start_index = None
                    break

    return functions

def extract_defines_structs_data(functions, input_file, output_dir):
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Regular expressions for #define, struct, and static const arrays
    define_pattern = re.compile(r'^\s*#define\s+\S+.*$', re.MULTILINE)
    struct_pattern = re.compile(r'\bstruct\s+\w+\s*\{[^}]+\};', re.MULTILINE | re.DOTALL)
    static_const_pattern = re.compile(r'static\s+const\s+[\w\d_]+\s+\w+\[[^\]]*\]\s*=\s*\{[^}]+\};', re.MULTILINE | re.DOTALL)
    enum_pattern = re.compile(r'\benum\s+\w*\s*\{[^}]+\};', re.MULTILINE | re.DOTALL)
    
    
    # Extract matches
    defines = define_pattern.findall(content)
    structs = struct_pattern.findall(content)
    static_consts = static_const_pattern.findall(content)
    enums = enum_pattern.findall(content)
    
    # Write to header file
    with open(os.path.join(output_dir, "flex_extraction.h"), 'w', encoding='utf-8') as f:
        f.write("#ifndef EXTRACTED_HEADER_H\n#define EXTRACTED_HEADER_H\n\n")
        
        if defines:
            f.write("// Extracted #defines\n")
            f.write("\n".join(defines) + "\n\n")

        if enums:
            f.write("// Extracted enums\n")
            f.write("\n\n".join(enums) + "\n\n")
        
        if structs:
            f.write("// Extracted structs\n")
            f.write("\n\n".join(structs) + "\n\n")
        
        if static_consts:
            f.write("// Extracted static const data\n")
            f.write("\n\n".join(static_consts) + "\n\n")
            
        if functions:
            f.write("\n".join(functions) + "\n\n")
        
        f.write("#endif // EXTRACTED_HEADER_H\n")

def extract_includes(c_file, source_dir):
    with open(c_file, 'r', encoding='utf-8') as file:
        code = file.readlines()

    includes = []
    local_headers = set()  # Store unique local header filenames

    # Regex pattern to match both quoted and angled bracket includes
    include_pattern = re.compile(r'#include\s+["<](.*?)[">]')

    for line in code:
        match = include_pattern.search(line)
        if match:
            header_file = match.group(1)
            includes.append(line.strip())  # Store full include statement

            # Check if the header exists in the source directory
            header_path = os.path.join(source_dir, header_file)
            if os.path.exists(header_path):
                local_headers.add(header_file)  # Track local headers

    return includes, local_headers

def copy_and_fix_headers(header_files, source_dir, output_dir):
    for header in header_files:
        source_path = os.path.join(source_dir, header)
        dest_path = os.path.join(output_dir, header)

        if os.path.exists(source_path):
            # Read the header file and replace <> with ""
            with open(source_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Convert #include <header.h> to #include "header.h"
            fixed_content = re.sub(r'#include\s+<([^>]+)>', r'#include "\1"', content)

            # Write the modified header to the output directory
            with open(dest_path, 'w', encoding='utf-8') as file:
                file.write(fixed_content)

            print(f"Copied and fixed: {header} to {output_dir}")
        else:
            print(f"Warning: Header file {header} not found in {source_dir}")

def extract_function_signatures(c_file):
    command = f'clang -E  {c_file} | cproto -s'

    # Run the command as a subprocess
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Capture the output and error messages
    output = result.stdout
    error = result.stderr

    if result.returncode != 0:
        print("Error:")
        print(error)
    
    functions = output.split('\n')
    functions = functions[1:]
    s_functions = {}
    for i in range(len(functions)):
        if "static" in functions[i]:
            functions[i] = functions[i].replace('static', '')
            s_functions[functions[i]] = True
        else:
            s_functions[functions[i]] = False
    
    return functions
    
def save_functions(functions, includes, local_headers, source_dir, output_dir):
    fixed_includes = []
    for line in includes:
        match = re.search(r'#include\s+["<](.*?)[">]', line)
        if match:
            header_file = match.group(1)
            if header_file in local_headers:
                fixed_includes.append(f'#include "{header_file}"') 
            else:
                fixed_includes.append(line)  # Keep system includes unchanged

    fixed_includes.append(f'#include "flex_extraction.h"')
    include_text = "\n".join(fixed_includes)

    for name, body in functions:
        body_clean = body.replace('static', '')
        function_dir = os.path.join(output_dir, name)
        os.makedirs(function_dir, exist_ok=True)

        # Write the .c file
        file_path = os.path.join(function_dir, f"{name}.c")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(include_text + "\n" + body_clean)

        # Copy flex_extraction.h into the function's directory
        src_header = os.path.join(output_dir, "flex_extraction.h")
        dst_header = os.path.join(function_dir, "flex_extraction.h")
        if os.path.exists(src_header):
            shutil.copy(src_header, dst_header)

        copy_and_fix_headers(local_headers, source_dir, function_dir)

def main():
    if len(sys.argv) < 2:
        print("Usage: process.py <filename.c>")
        print("<filename.c> is the name of the c file to split into its functions.")

    c_filename = sys.argv[1]
    output_directory = f"bms/c/gt_{c_filename}"
    source_directory = os.path.dirname(os.path.abspath(c_filename))

    extracted_includes, local_headers = extract_includes(c_filename, source_directory)
    signatures = extract_function_signatures(c_filename) 
    extracted_functions = extract_functions(c_filename)
    

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    

    extract_defines_structs_data(signatures, c_filename, output_directory)

    save_functions(extracted_functions, extracted_includes, local_headers, source_directory, output_directory)

    print(f"Extracted {len(extracted_functions)} functions into '{output_directory}' with includes and headers copied & fixed.")

if __name__ == "__main__":
    main()