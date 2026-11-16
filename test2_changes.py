from openai import OpenAI
import os
import sys
import subprocess
import tempfile
import time
import signal

# Retrieve the API key from the environment variable.
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set. Please set it or provide your API key directly.")
    sys.exit(1)

client = OpenAI(api_key=api_key)

def call_chat_completion(model, messages, temperature=0.3):
    """
    Helper function that wraps client.chat.completions.create.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response
    except Exception as e:
        error_message = (
            "Error calling client.chat.completions.create. It appears that your installed "
            "OpenAI Python package version is incompatible with this call.\n"
            "Please run `openai migrate` to update your codebase or pin your openai package "
            "to an earlier version (e.g., `pip install openai==0.28.0`)."
        )
        print(error_message, file=sys.stderr)
        raise e

def planner_agent(source_code, source_lang, target_lang):
    prompt = (
        f"Analyze the following {source_lang} code and generate a detailed conversion plan "
        f"for translating it to {target_lang}. The plan should include a mapping for functions, "
        f"libraries, and all necessary modifications.\n\nSource Code:\n{source_code}\n"
        f"Do not give me the entire code, I just want the plan."
        f"The output will be used as prompt further so remove all formattting and keep it concise\n"
    )
    messages = [
        {"role": "system", "content": "You are a code planning agent."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="gpt-4o-mini", messages=messages, temperature=0.3)
    plan = response.choices[0].message.content
    return plan

def converter_agent(plan, source_code, source_lang, target_lang, feedback_context=""):
    feedback_text = f"\n\nPrevious evaluator feedback:\n{feedback_context}\n" if feedback_context else ""
    prompt = (
        f"Using the following conversion plan:\n{plan}\n"
        f"{feedback_text}"
        f"Convert the following {source_lang} code into {target_lang}. "
        f"Ensure the resulting code is syntactically and semantically equivalent to the original.\n"
        f"Remove all explanatory strings before and after the code\n\n"
        f"Source Code:\n{source_code}\n"
    )
    messages = [
        {"role": "system", "content": "You are a code conversion agent."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="gpt-4o-mini", messages=messages, temperature=0.3)
    converted_code = response.choices[0].message.content
    return converted_code

def evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output, program_output):
    prompt = (
        f"Evaluate the conversion of the following {source_lang} code into {target_lang}.\n\n"
        f"Original Code:\n{source_code}\n\n"
        f"Converted Code:\n{converted_code}\n\n"
        "Evaluate the syntactic correctness and semantic equivalence of "
        "the converted code which is executed locally and produced the output provided below. "
        "Simulate running the converted code with the test input provided and verify that "
        "the program output matches the ideal output.\n\n"
        f"Test Input:\n{test_input}\n\n"
        f"Ideal Output:\n{ideal_output}\n\n"
        f"Program Output:\n{program_output}\n\n"
        "If the converted code is acceptable on all counts, start your response with 'PASS:' "
        "followed by a brief summary of why it passed. Otherwise, start your response with 'FAIL:' "
        "and provide feedback on what needs to be improved."
    )
    messages = [
        {"role": "system", "content": "You are a code evaluation agent."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="gpt-4o-mini", messages=messages, temperature=0.3)
    evaluation = response.choices[0].message.content
    return evaluation

def run_converted_code(converted_code, target_lang):
    """
    Writes the converted code to a temporary file, runs it using the appropriate interpreter,
    and returns the output (stdout and stderr).
    Supports Python, JavaScript, Java, C++, C#, PHP, and C.
    """
    # Language configuration mapping
    lang_config = {
        "python": {"suffix": ".py", "command": ["python"]},
        "javascript": {"suffix": ".js", "command": ["node"]},
        "java": {"suffix": ".java", "compile": ["javac"], "run": ["java"]},
        "cpp": {"suffix": ".cpp", "compile": ["g++", "-o"], "run": ["./"]},
        "csharp": {"suffix": ".cs", "compile": ["dotnet", "build"], "run": ["dotnet", "run"]},
        "php": {"suffix": ".php", "command": ["php"]},
        "c": {"suffix": ".c", "compile": ["gcc", "-o"], "run": ["./"]}
    }

    # Get language configuration
    config = lang_config.get(target_lang.lower())
    if not config:
        print(f"Execution for target language '{target_lang}' is not supported.")
        return "Execution not supported for this language."

    # Create a temporary file to hold the converted code
    with tempfile.NamedTemporaryFile(mode="w", suffix=config["suffix"], delete=False) as tmp_file:
        tmp_file.write(converted_code)
        tmp_file_path = tmp_file.name
        base_name = os.path.splitext(tmp_file_path)[0]

    try:
        # Handle compilation for languages that need it
        if "compile" in config:
            compile_cmd = config["compile"] + [tmp_file_path]
            if "run" in config and config["run"][0] == "./":
                compile_cmd.append(base_name)
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if compile_result.returncode != 0:
                return f"Compilation error: {compile_result.stderr}"

        # Prepare run command
        if "command" in config:
            run_cmd = config["command"] + [tmp_file_path]
        else:
            run_cmd = config["run"] + [base_name]

        # Execute the code
        result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + "\n" + result.stderr

    except subprocess.TimeoutExpired:
        output = "Error: Execution timed out after 30 seconds"
    except Exception as e:
        output = f"Error during execution: {str(e)}"
    finally:
        # Clean up temporary files
        try:
            os.remove(tmp_file_path)
            if "compile" in config:
                os.remove(base_name)
        except:
            pass

    return output

def aci_executor(converted_code, target_lang, test_input=None, ideal_output=None):
    """
    Automated Code Integration executor that runs the code and validates its output.
    Returns a tuple of (success, output, error_message, final_code, process_output)
    """
    # Extract code between triple backticks
    code_lines = converted_code.strip().split('\n')
    cleaned_code = []
    in_code_block = False
    found_last_backticks = False
    
    for line in code_lines:
        if found_last_backticks:
            break
            
        if line.strip().startswith('```'):
            if not in_code_block:
                # Skip the language marker on the same line as opening backticks
                in_code_block = True
            else:
                in_code_block = False
                found_last_backticks = True
            continue
        if in_code_block:
            cleaned_code.append(line)
    
    if not cleaned_code:
        # If no code block found, use the original code
        cleaned_code = code_lines
    
    final_code = '\n'.join(cleaned_code)

    # Language configuration mapping
    lang_config = {
        "python": {"suffix": ".py", "command": ["python"]},
        "javascript": {"suffix": ".js", "command": ["node"]},
        "java": {"suffix": ".java", "compile": ["javac"], "run": ["java"]},
        "cpp": {"suffix": ".cpp", "compile": ["g++", "-o"], "run": ["./"]},
        "csharp": {"suffix": ".cs", "compile": ["dotnet", "build"], "run": ["dotnet", "run"]},
        "php": {"suffix": ".php", "command": ["php"]},
        "c": {"suffix": ".c", "compile": ["gcc", "-o"], "run": ["./"]}
    }

    # Get language configuration
    config = lang_config.get(target_lang.lower())
    if not config:
        return False, None, f"Execution for target language '{target_lang}' is not supported.", None

    # Create a temporary file for the code
    with tempfile.NamedTemporaryFile(mode="w", suffix=config["suffix"], delete=False) as tmp_file:
        tmp_file.write(final_code)
        tmp_file_path = tmp_file.name
        base_name = os.path.splitext(tmp_file_path)[0]

    try:
        # Handle compilation for languages that need it
        if "compile" in config:
            compile_cmd = config["compile"] + [tmp_file_path]
            if "run" in config and config["run"][0] == "./":
                compile_cmd.append(base_name)
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if compile_result.returncode != 0:
                return False, None, f"Compilation error: {compile_result.stderr}", None

        # Prepare run command
        if "command" in config:
            run_cmd = config["command"] + [tmp_file_path]
        else:
            run_cmd = config["run"] + [base_name]

        # Set up process with timeout
        process = subprocess.Popen(
            run_cmd,
            stdin=subprocess.PIPE if test_input else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # If there's test input, send it to the process
        if test_input:
            process.stdin.write(test_input)
            process.stdin.close()

        # Wait for process with timeout
        try:
            stdout, stderr = process.communicate(timeout=90)  # 1.5 minutes timeout
        except subprocess.TimeoutExpired:
            process.kill()
            return False, None, "Process timed out after 1.5 minutes", None

        # Check if process completed successfully
        if process.returncode != 0:
            return False, None, f"Process failed with error: {stderr}", None

        # If we have an ideal output, compare it
        if ideal_output:
            actual_output = stdout.strip()
            if actual_output != ideal_output.strip():
                return False, actual_output, f"Output mismatch. Expected: {ideal_output}, Got: {actual_output}", None

        return True, stdout, None, final_code

    except Exception as e:
        return False, None, f"Error during execution: {str(e)}", None
    finally:
        # Clean up temporary files
        try:
            os.remove(tmp_file_path)
            if "compile" in config:
                os.remove(base_name)
        except:
            pass

def save_code_to_file(code, target_lang):
    """Save the converted code to a file in the working directory"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    lang_config = {
        "python": ".py",
        "javascript": ".js",
        "java": ".java",
        "cpp": ".cpp",
        "csharp": ".cs",
        "php": ".php",
        "c": ".c"
    }
    extension = lang_config.get(target_lang.lower(), ".txt")
    filename = f"converted_code_{timestamp}{extension}"
    
    with open(filename, "w") as f:
        if code!=None:
            f.write(code)
    return filename

def main():
    # Read source code from file
    with open('source_code.txt','r') as f:
        source_code = f.read()
    print(source_code)

    source_lang = input("Enter the source language (e.g., Python): ").strip()
    target_lang = input("Enter the target language (e.g., JavaScript): ").strip()
    # with open ('input.txt','r') as f:
    #     test_input = f.readlines()
    # with open ('output.txt','r') as f:
    #     ideal_output = f.readlines()

    print("\n=== Invoking Planner Agent ===")
    plan = planner_agent(source_code, source_lang, target_lang)
    print("Planner Agent Output:")
    print(plan)

    max_attempts = 5
    attempt = 0
    feedback_context = ""
    last_converted_code = None
    aci_failed = False

    while attempt < max_attempts:
        print(f"\n=== Attempt {attempt + 1}: Invoking Converter Agent ===")
        converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
        print("Converter Agent Output:")
        print(converted_code)
        last_converted_code = converted_code

        if not aci_failed:
            print("\n=== Running ACI Executor ===")
            success, output, error, final_code = aci_executor(converted_code, target_lang, test_input, ideal_output)

            if success:
                print("ACI Execution successful!")
                # Save the successful code to a file
                filename = save_code_to_file(final_code, target_lang)
                print(f"\nCode saved to: {filename}")
                
                # Save ACI output to file
                with open('aci_output.txt', 'w') as f:
                    f.write(f"=== ACI Execution Output ===\n")
                    f.write(f"Test Input: {test_input}\n")
                    f.write(f"Ideal Output: {ideal_output}\n")
                    f.write(f"Actual Output: {output}\n")
                    f.write(f"Generated Code:\n{final_code}\n")
                print(f"ACI output saved to: aci_output.txt")
                
                print("\n[Final Output] Converted Code:")
                print(final_code)
                return
            else:
                print(f"ACI Execution failed: {error}")
                if output:
                    print(f"Program output: {output}")
                aci_failed = True
                # Create feedback for the planner
                feedback_context = f"Previous attempt failed with error: {error}\n"
                if output:
                    feedback_context += f"Program output: {output}\n"
        else:
            # If ACI has failed before, use evaluator LLM directly
            print("\n=== Running Evaluator LLM ===")
            evaluation = evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output, output)
            print("Evaluator Output:")
            print(evaluation)

            if evaluation.strip().upper().startswith("PASS:"):
                print("\nEvaluation successful!")
                # Extract code between triple backticks
                code_lines = converted_code.strip().split('\n')
                cleaned_code = []
                in_code_block = False
                found_last_backticks = False
                
                for line in code_lines:
                    if found_last_backticks:
                        break
                        
                    if line.strip().startswith('```'):
                        if not in_code_block:
                            # Skip the language marker on the same line as opening backticks
                            in_code_block = True
                        else:
                            in_code_block = False
                            found_last_backticks = True
                        continue
                    if in_code_block:
                        cleaned_code.append(line)
                
                if not cleaned_code:
                    # If no code block found, use the original code
                    cleaned_code = code_lines
                
                modified_code = '\n'.join(cleaned_code)
                
                # Save the successful code to a file
                filename = save_code_to_file(modified_code, target_lang)
                print(f"\nCode saved to: {filename}")
                print("\n[Final Output] Converted Code:")
                print(modified_code)
                return
            else:
                print("\nEvaluation did not pass. Regenerating code using feedback...")
                feedback_context = evaluation

        attempt += 1

    # If we've exhausted all attempts, return the last converted code
    if last_converted_code:
        print("\n[Final Output] Using last generated code after maximum attempts:")
        print(last_converted_code)
        # Save the last code to a file
        filename = save_code_to_file(last_converted_code, target_lang)
        print(f"\nCode saved to: {filename}")
    else:
        print("\n[Final Output] Conversion failed after maximum attempts. Last error:")
        print(feedback_context)

if __name__ == "__main__":
    main()


