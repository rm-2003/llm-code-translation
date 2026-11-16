from groq import Groq
import os
import sys
import subprocess
import tempfile
import time
import signal

# api_key = "YOUR_GROQ_API_KEY"

# Retrieve the API key from the environment variable.
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("Error: GROQ_API_KEY environment variable not set. Please set it or provide your API key directly.")
    sys.exit(1)

client = Groq(api_key=api_key)

def call_chat_completion(model, messages, temperature=0.3):
    """
    Helper function that wraps client.chat.completions.create.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
            top_p=0.95
        )
        return response
    except Exception as e:
        error_message = (
            "Error calling client.chat.completions.create. It appears that your installed "
            "Groq Python package version is incompatible with this call.\n"
            "Please ensure you have the latest version of the groq package installed."
        )
        print(error_message, file=sys.stderr)
        raise e

def planner_agent(source_code, source_lang, target_lang):
    prompt = (
        f"Analyze the following {source_lang} code and generate a detailed conversion plan "
        f"for translating it to {target_lang}. The plan should include a mapping for functions, "
        f"libraries, and any necessary modifications.\n\nSource Code:\n{source_code}\n"
        f"Do not give me the entire code, I just want the plan."
        f"The output will be used as prompt further so remove all formattting and keep it concise\n"
    )
    messages = [
        {"role": "system", "content": "You are a code planning agent specialized in code conversion and language mapping."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="deepseek-r1-distill-llama-70b", messages=messages, temperature=0.3)
    plan = response.choices[0].message.content
    return plan

def converter_agent(plan, source_code, source_lang, target_lang, feedback_context=""):
    feedback_text = f"\n\nPrevious evaluator feedback:\n{feedback_context}\n" if feedback_context else ""
    prompt = (
        f"Using the following conversion plan:\n{plan}\n"
        f"{feedback_text}"
        f"Convert the following {source_lang} code into {target_lang}. "
        f"Ensure the resulting code is syntactically and semantically equivalent to the original.\n\n"
        f"Remove all explanatory strings before and after the code\n\n"
        f"Source Code:\n{source_code}\n"
    )
    messages = [
        {"role": "system", "content": "You are a code conversion agent specialized in accurate language translation."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="deepseek-r1-distill-llama-70b", messages=messages, temperature=0.3)
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
        {"role": "system", "content": "You are a code evaluation agent specialized in code correctness and equivalence verification."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="deepseek-r1-distill-llama-70b", messages=messages, temperature=0.3)
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
    Returns a tuple of (success, output, error_message, final_code)
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

    # For Java, we need to handle the class name and file name matching
    if target_lang.lower() == "java":
        # Extract the public class name from the code
        class_name = None
        for line in cleaned_code:
            if "public class" in line:
                class_name = line.split("public class")[1].split("{")[0].strip()
                break
        
        if not class_name:
            return False, None, "No public class found in Java code", None

        # Create a temporary directory for Java files
        temp_dir = tempfile.mkdtemp()
        try:
            # Create the Java file with the correct class name
            java_file_path = os.path.join(temp_dir, f"{class_name}.java")
            with open(java_file_path, 'w') as f:
                f.write(final_code)
            
            # Compile the Java file
            compile_result = subprocess.run(
                config["compile"] + [java_file_path],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if compile_result.returncode != 0:
                return False, None, f"Compilation error: {compile_result.stderr}", None

            # Run the Java program
            try:
                result = subprocess.run(
                    config["run"] + [class_name],
                    input=test_input if test_input else None,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    cwd=temp_dir
                )
                
                # Check if process completed successfully
                if result.returncode != 0:
                    return False, None, f"Process failed with error: {result.stderr}", None

                # If we have an ideal output, compare it
                all_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
                ideal = ideal_output.strip()
                # try to find a line that contains the ideal output
                match_line = next((ln for ln in all_lines if ideal in ln), None)
                if match_line:
                    # pull out exactly the ideal substring
                    start = match_line.find(ideal)
                    actual_output = match_line[start:start+len(ideal)]
                else:
                    # fallback: last non-empty line
                    actual_output = all_lines[-1] if all_lines else ""
                
                if actual_output != ideal:
                    return False, actual_output, (
                        f"Output mismatch.\n"
                        f"  Expected: {ideal}\n"
                        f"    Actual: {actual_output}"
                    ), None

                return True, actual_output, None, final_code

            except subprocess.TimeoutExpired:
                return False, None, "Process timed out after 1.5 minutes", None
            except Exception as e:
                return False, None, f"Error during execution: {str(e)}", None

        finally:
            # Clean up the temporary directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass

    else:
        # For other languages, proceed as normal
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

            # Execute the code with input
            try:
                result = subprocess.run(
                    run_cmd,
                    input=test_input if test_input else None,
                    capture_output=True,
                    text=True,
                    timeout=90  # 1.5 minutes timeout
                )
                
                # Check if process completed successfully
                if result.returncode != 0:
                    return False, None, f"Process failed with error: {result.stderr}", None

                # If we have an ideal output, compare it
                all_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
                ideal = ideal_output.strip()
                # try to find a line that contains the ideal output
                match_line = next((ln for ln in all_lines if ideal in ln), None)
                if match_line:
                    # pull out exactly the ideal substring
                    start = match_line.find(ideal)
                    actual_output = match_line[start:start+len(ideal)]
                else:
                    # fallback: last non-empty line
                    actual_output = all_lines[-1] if all_lines else ""
                
                if actual_output != ideal:
                    return False, actual_output, (
                        f"Output mismatch.\n"
                        f"  Expected: {ideal}\n"
                        f"    Actual: {actual_output}"
                    ), None

                return True, actual_output, None, final_code

            except subprocess.TimeoutExpired:
                return False, None, "Process timed out after 1.5 minutes", None
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

    return False, None, "ACI execution failed", None

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

def analyze_input_requirements(source_code, source_lang):
    """
    Analyzes the source code to determine what input parameters are needed.
    Returns a list of input parameters with their types and descriptions.
    """
    prompt = (
        f"Analyze the following {source_lang} code and list all input parameters needed to run it. "
        f"Return only the parameters as mentioned below, not any explanation or comments."
        f"For each parameter, specify its type, a brief description, and whether it expects multiple values on the same line.\n\n"
        f"Source Code:\n{source_code}\n\n"
        f"Return the response in this exact format:\n"
        f"PARAM_NAME:TYPE:DESCRIPTION:MULTI_LINE\n"
        f"Example:\n"
        f"age:int:Age of the person:false\n"
        f"numbers:int:List of numbers to sort:true\n"
        f"If no input is needed, return 'NO_INPUT'"
    )
    
    messages = [
        {"role": "system", "content": "You are an input analysis agent specialized in code analysis."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_chat_completion(model="deepseek-r1-distill-llama-70b", messages=messages, temperature=0.3)
    return response.choices[0].message.content.strip()

def get_user_inputs(input_requirements):
    """
    Prompts the user for each required input parameter and returns them as a list.
    """
    if input_requirements == "NO_INPUT":
        return []
    
    inputs = []
    for line in input_requirements.split('\n'):
        if not line.strip():
            continue
            
        param_name, param_type, description, multi_line = line.split(':')
        while True:
            try:
                if multi_line.lower() == 'true':
                    # For multi-line inputs, get all values at once
                    user_input = input(f"Enter {description} ({param_type}, space-separated): ").strip()
                    if param_type == "int":
                        values = [int(x) for x in user_input.split()]
                    elif param_type == "float":
                        values = [float(x) for x in user_input.split()]
                    else:  # str or any other type
                        values = user_input.split()
                    inputs.extend([str(x) for x in values])
                else:
                    # For single-line inputs
                    user_input = input(f"Enter {description} ({param_type}): ").strip()
                    if param_type == "int":
                        value = int(user_input)
                    elif param_type == "float":
                        value = float(user_input)
                    elif param_type == "bool":
                        value = user_input.lower() in ['true', 'yes', '1']
                    else:  # str or any other type
                        value = user_input
                    inputs.append(str(value))
                break
            except ValueError:
                print(f"Invalid input. Please enter valid {param_type}(s).")
    
    return inputs

def generate_test_cases(source_code, source_lang, target_lang):
    """
    Uses LLM to generate appropriate test cases for the given code.
    Returns a tuple of (test_input, expected_output)
    """
    prompt = (
        f"Analyze the following {source_lang} code and generate a test case with input and expected output.\n"
        f"The code will be converted to {target_lang}, so make sure the test case is language-agnostic.\n\n"
        f"Source Code:\n{source_code}\n\n"
        f"Return the response in this exact format:\n"
        f"INPUT:\n<test input>\n"
        f"OUTPUT:\n<expected output>\n"
    )
    
    messages = [
        {"role": "system", "content": "You are a test case generation agent."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_chat_completion(model="deepseek-r1-distill-llama-70b", messages=messages, temperature=0.3)
    result = response.choices[0].message.content.strip()
    
    # Parse the response
    try:
        input_section = result.split("INPUT:")[1].split("OUTPUT:")[0].strip()
        output_section = result.split("OUTPUT:")[1].strip()
        return input_section, output_section
    except:
        return "", ""

def main():
    # Read source code from file
    with open('source_code.txt','r') as f:
        source_code = f.read()
    print(source_code)

    source_lang = input("Enter the source language (e.g., Python): ").strip()
    target_lang = input("Enter the target language (e.g., JavaScript): ").strip()
    
    # Ask if user wants to provide input/output
    use_io = input("\nDo you want to provide input and expected output? (yes/no): ").strip().lower()
    
    test_input = ""
    ideal_output = ""
    
    if use_io == "yes":
        # Analyze input requirements
        print("\n=== Analyzing Input Requirements ===")
        input_requirements = analyze_input_requirements(source_code, source_lang)
        print("Input Requirements:")
        print(input_requirements)
        
        # Get user inputs
        test_inputs = get_user_inputs(input_requirements)
        test_input = '\n'.join(test_inputs) if test_inputs else ""
        
        # Get expected output
        ideal_output = input("Enter the expected output: ").strip()

    print("\n=== Invoking Planner Agent ===")
    plan = planner_agent(source_code, source_lang, target_lang)
    print("Planner Agent Output:")
    print(plan)

    max_attempts = 5
    attempt = 0
    feedback_context = ""
    last_converted_code = None
    aci_success = False
    last_error = None
    consecutive_same_error = 0

    # First try ACI without input to check if code compiles
    if use_io == "no":
        print("\n=== First ACI attempt without input ===")
        converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
        print("Converter Agent Output:")
        print(converted_code)
        last_converted_code = converted_code

        print("\n=== Running ACI Executor without input ===")
        success, output, error, final_code = aci_executor(converted_code, target_lang, "", "")

        if not success:
            print(f"Initial ACI attempt failed: {error}")
            print("\n=== Generating test cases using LLM ===")
            test_input, ideal_output = generate_test_cases(source_code, source_lang, target_lang)
            print(f"Generated test input: {test_input}")
            print(f"Generated expected output: {ideal_output}")
        else:
            print("Initial ACI attempt successful! Code compiles and runs without input.")
            # Save the successful code to a file
            filename = save_code_to_file(final_code, target_lang)
            print(f"\nCode saved to: {filename}")
            print("\n[Final Output] Converted Code:")
            print(final_code)
            return

    # Try ACI with input/output (either user-provided or generated)
    while attempt < max_attempts and not aci_success:
        print(f"\n=== Attempt {attempt + 1}: Invoking Converter Agent ===")
        converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
        print("Converter Agent Output:")
        print(converted_code)
        last_converted_code = converted_code

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
            aci_success = True
            return
        else:
            print(f"ACI Execution failed: {error}")
            if output:
                print(f"Program output: {output}")
            
            # Check if this is the same error as the last attempt
            if error == last_error:
                consecutive_same_error += 1
                if consecutive_same_error >= 2:
                    print("\n=== Same error occurred twice consecutively. Switching to Evaluator LLM ===")
                    break
            else:
                consecutive_same_error = 1
                last_error = error
            
            # Create feedback for the planner
            feedback_context = f"Previous attempt failed with error: {error}\n"
            if output:
                feedback_context += f"Program output: {output}\n"
            attempt += 1

    # If ACI failed, try with Evaluator LLM
    if not aci_success:
        print("\n=== Using Evaluator LLM ===")
        attempt = 0
        while attempt < max_attempts:
            # Use the last converted code from ACI attempts
            if attempt == 0 and last_converted_code:
                print("\n=== Using last generated code from ACI attempts ===")
                converted_code = last_converted_code
            else:
                print(f"\n=== Attempt {attempt + 1}: Invoking Converter Agent ===")
                converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
                print("Converter Agent Output:")
                print(converted_code)
                last_converted_code = converted_code

            print("\n=== Running Evaluator LLM ===")
            evaluation = evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output, "")
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


