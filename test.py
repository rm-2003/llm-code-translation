# import openai
# import os

# # Set your OpenAI API key (either set the environment variable or specify directly)
# openai.api_key = os.getenv("OPENAI_API_KEY")  # or: openai.api_key = "your-api-key-here"

# def planner_agent(source_code, source_lang, target_lang):
#     """
#     Planner agent: Analyzes the input code and produces a conversion plan.
#     Uses the 'openai-4o' model.
#     """
#     prompt = (
#         f"Analyze the following {source_lang} code and generate a detailed conversion plan "
#         f"for translating it to {target_lang}. The plan should include a mapping for functions, "
#         f"libraries, and any necessary modifications. \n\nSource Code:\n{source_code}\n"
#     )
#     response = openai.ChatCompletion.create(
#         model="openai-4o",  # Replace with your actual model name
#         messages=[
#             {"role": "system", "content": "You are a code planning agent."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.3
#     )
#     plan = response['choices'][0]['message']['content']
#     return plan

# def converter_agent(plan, source_code, source_lang, target_lang, feedback_context=""):
#     """
#     Converter agent: Translates the source code into the target language using the conversion plan.
#     Uses the 'o3-mini-high' model.
#     Optionally, includes previous evaluator feedback to refine the conversion.
#     """
#     feedback_text = f"\n\nPrevious evaluator feedback:\n{feedback_context}\n" if feedback_context else ""
#     prompt = (
#         f"Using the following conversion plan:\n{plan}\n"
#         f"{feedback_text}"
#         f"Convert the following {source_lang} code into {target_lang}. "
#         f"Ensure the resulting code is syntactically and semantically equivalent to the original. \n\n"
#         f"Source Code:\n{source_code}\n"
#     )
#     response = openai.ChatCompletion.create(
#         model="o3-mini-high",  # Replace with your actual model name
#         messages=[
#             {"role": "system", "content": "You are a code conversion agent."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.3
#     )
#     converted_code = response['choices'][0]['message']['content']
#     return converted_code

# def evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output):
#     """
#     Evaluator agent: Compares the original and converted code for syntactic correctness, semantic equivalence,
#     and checks whether the converted code produces the expected output when executed with a given test input.
#     Uses the 'oo' model.
#     The evaluator's response should start with "PASS:" if the conversion is acceptable,
#     or "FAIL:" with feedback if not.
#     """
#     prompt = (
#         f"Evaluate the conversion of the following {source_lang} code into {target_lang}.\n\n"
#         f"Original Code:\n{source_code}\n\nConverted Code:\n{converted_code}\n\n"
#         "In addition to checking for syntactic correctness and semantic equivalence, simulate running "
#         "the converted code with the test input provided below. Verify that the output matches the ideal output.\n\n"
#         f"Test Input:\n{test_input}\n\n"
#         f"Ideal Output:\n{ideal_output}\n\n"
#         "If the converted code is acceptable on all counts, start your response with 'PASS:' followed by "
#         "a brief summary of why it passed. Otherwise, start your response with 'FAIL:' and provide feedback on "
#         "what needs to be improved."
#     )
#     response = openai.ChatCompletion.create(
#         model="oo",  # Replace with your actual model name
#         messages=[
#             {"role": "system", "content": "You are a code evaluation agent."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.3
#     )
#     evaluation = response['choices'][0]['message']['content']
#     return evaluation

# def main():
#     # Prompt user for custom input
#     print("Enter the source code (press Enter when done):")
#     source_code = []
#     while True:
#         line = input()
#         if line == "":
#             break
#         source_code.append(line)
#     source_code = "\n".join(source_code)

#     source_lang = input("Enter the source language (e.g., Python): ").strip()
#     target_lang = input("Enter the target language (e.g., JavaScript): ").strip()
#     test_input = input("Enter test input for the converted code (leave blank if not needed): ").strip()
#     ideal_output = input("Enter the ideal output for the given test input: ").strip()

#     print("\n=== Invoking Planner Agent ===")
#     plan = planner_agent(source_code, source_lang, target_lang)
#     print("Planner Agent Output:")
#     print(plan)

#     max_attempts = 5  # To avoid an infinite loop in case of repeated failures.
#     attempt = 0
#     feedback_context = ""
#     final_converted_code = None

#     while attempt < max_attempts:
#         print(f"\n=== Attempt {attempt + 1}: Invoking Converter Agent ===")
#         converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
#         print("Converter Agent Output:")
#         print(converted_code)

#         print("\n=== Invoking Evaluator Agent ===")
#         evaluation = evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output)
#         print("Evaluator Agent Output:")
#         print(evaluation)

#         # Check if evaluation starts with "PASS:" (indicating satisfaction)
#         if evaluation.strip().upper().startswith("PASS:"):
#             final_converted_code = converted_code
#             print("\nConversion successful!")
#             break
#         else:
#             # Use evaluator feedback to refine the conversion.
#             feedback_context = evaluation
#             print("\nEvaluator did not pass the conversion. Regenerating code using evaluator feedback...")
#             attempt += 1

#     if final_converted_code:
#         print("\n[Final Output] Converted Code:")
#         print(final_converted_code)
#     else:
#         print("\n[Final Output] Conversion failed after maximum attempts. Last evaluation feedback:")
#         print(feedback_context)

# if __name__ == "__main__":
#     main()


# from openai import OpenAI

# import os
# import sys
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # Set your OpenAI API key (either via the environment variable or directly here)
#   # or: openai.api_key = "your-api-key-here"

# def call_chat_completion(model, messages, temperature=0.3):
#     """
#     Helper function that wraps openai.ChatCompletion.create.
#     If an APIRemovedInV1 error (or similar) occurs, it prints instructions
#     on how to resolve the issue.
#     """
#     try:
#         response = client.chat.completions.create(model=model,
#         messages=messages,
#         temperature=temperature)
#         return response
#     except Exception as e:
#         error_message = (
#             "Error calling openai.ChatCompletion.create. It appears that your installed "
#             "OpenAI Python package version is incompatible with this call.\n"
#             "Please run `openai migrate` to update your codebase or pin your openai package "
#             "to an earlier version (e.g., `pip install openai==0.28.0`)."
#         )
#         print(error_message, file=sys.stderr)
#         raise e

# def planner_agent(source_code, source_lang, target_lang):
#     """
#     Planner agent: Analyzes the input code and produces a conversion plan.
#     Uses the 'openai-4o' model.
#     """
#     prompt = (
#         f"Analyze the following {source_lang} code and generate a detailed conversion plan "
#         f"for translating it to {target_lang}. The plan should include a mapping for functions, "
#         f"libraries, and any necessary modifications.\n\nSource Code:\n{source_code}\n"
#     )
#     messages = [
#         {"role": "system", "content": "You are a code planning agent."},
#         {"role": "user", "content": prompt}
#     ]
#     response = call_chat_completion(model="openai-4o", messages=messages, temperature=0.3)
#     plan = response.choices[0].message.content
#     return plan

# def converter_agent(plan, source_code, source_lang, target_lang, feedback_context=""):
#     """
#     Converter agent: Translates the source code into the target language using the conversion plan.
#     Uses the 'o3-mini-high' model.
#     Optionally, includes previous evaluator feedback to refine the conversion.
#     """
#     feedback_text = f"\n\nPrevious evaluator feedback:\n{feedback_context}\n" if feedback_context else ""
#     prompt = (
#         f"Using the following conversion plan:\n{plan}\n"
#         f"{feedback_text}"
#         f"Convert the following {source_lang} code into {target_lang}. "
#         f"Ensure the resulting code is syntactically and semantically equivalent to the original.\n\n"
#         f"Source Code:\n{source_code}\n"
#     )
#     messages = [
#         {"role": "system", "content": "You are a code conversion agent."},
#         {"role": "user", "content": prompt}
#     ]
#     response = call_chat_completion(model="o3-mini-high", messages=messages, temperature=0.3)
#     converted_code = response.choices[0].message.content
#     return converted_code

# def evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output):
#     """
#     Evaluator agent: Compares the original and converted code for syntactic correctness, semantic equivalence,
#     and checks whether the converted code produces the expected output when executed with a given test input.
#     Uses the 'oo' model.
#     The evaluator's response should start with "PASS:" if the conversion is acceptable,
#     or "FAIL:" with feedback if not.
#     """
#     prompt = (
#         f"Evaluate the conversion of the following {source_lang} code into {target_lang}.\n\n"
#         f"Original Code:\n{source_code}\n\nConverted Code:\n{converted_code}\n\n"
#         "In addition to checking for syntactic correctness and semantic equivalence, simulate running "
#         "the converted code with the test input provided below. Verify that the output matches the ideal output.\n\n"
#         f"Test Input:\n{test_input}\n\n"
#         f"Ideal Output:\n{ideal_output}\n\n"
#         "If the converted code is acceptable on all counts, start your response with 'PASS:' followed by "
#         "a brief summary of why it passed. Otherwise, start your response with 'FAIL:' and provide feedback on "
#         "what needs to be improved."
#     )
#     messages = [
#         {"role": "system", "content": "You are a code evaluation agent."},
#         {"role": "user", "content": prompt}
#     ]
#     response = call_chat_completion(model="oo", messages=messages, temperature=0.3)
#     evaluation = response.choices[0].message.content
#     return evaluation

# def main():
#     # Prompt user for custom input
#     print("Enter the source code (press Enter on an empty line to finish):")
#     source_code_lines = []
#     while True:
#         line = input()
#         if line == "":
#             break
#         source_code_lines.append(line)
#     source_code = "\n".join(source_code_lines)

#     source_lang = input("Enter the source language (e.g., Python): ").strip()
#     target_lang = input("Enter the target language (e.g., JavaScript): ").strip()
#     test_input = input("Enter test input for the converted code (leave blank if not needed): ").strip()
#     ideal_output = input("Enter the ideal output for the given test input: ").strip()

#     print("\n=== Invoking Planner Agent ===")
#     plan = planner_agent(source_code, source_lang, target_lang)
#     print("Planner Agent Output:")
#     print(plan)

#     max_attempts = 5  # Avoid infinite loop if conversion repeatedly fails.
#     attempt = 0
#     feedback_context = ""
#     final_converted_code = None

#     while attempt < max_attempts:
#         print(f"\n=== Attempt {attempt + 1}: Invoking Converter Agent ===")
#         converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
#         print("Converter Agent Output:")
#         print(converted_code)

#         print("\n=== Invoking Evaluator Agent ===")
#         evaluation = evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output)
#         print("Evaluator Agent Output:")
#         print(evaluation)

#         # Check if evaluation starts with "PASS:" (indicating success)
#         if evaluation.strip().upper().startswith("PASS:"):
#             final_converted_code = converted_code
#             print("\nConversion successful!")
#             break
#         else:
#             # Use evaluator feedback to refine the conversion.
#             feedback_context = evaluation
#             print("\nEvaluator did not pass the conversion. Regenerating code using evaluator feedback...")
#             attempt += 1

#     if final_converted_code:
#         print("\n[Final Output] Converted Code:")
#         print(final_converted_code)
#     else:
#         print("\n[Final Output] Conversion failed after maximum attempts. Last evaluation feedback:")
#         print(feedback_context)

# if __name__ == "__main__":
#     main()


from openai import OpenAI
import os
import sys

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
        f"libraries, and any necessary modifications.\n\nSource Code:\n{source_code}\n"
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
        f"Ensure the resulting code is syntactically and semantically equivalent to the original.\n\n"
        f"Source Code:\n{source_code}\n"
    )
    messages = [
        {"role": "system", "content": "You are a code conversion agent."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="gpt-4o-mini", messages=messages, temperature=0.3)
    converted_code = response.choices[0].message.content
    return converted_code

def evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output):
    prompt = (
        f"Evaluate the conversion of the following {source_lang} code into {target_lang}.\n\n"
        f"Original Code:\n{source_code}\n\nConverted Code:\n{converted_code}\n\n"
        "In addition to checking for syntactic correctness and semantic equivalence, simulate running "
        "the converted code with the test input provided below. Verify that the output matches the ideal output.\n\n"
        f"Test Input:\n{test_input}\n\n"
        f"Ideal Output:\n{ideal_output}\n\n"
        "If the converted code is acceptable on all counts, start your response with 'PASS:' followed by "
        "a brief summary of why it passed. Otherwise, start your response with 'FAIL:' and provide feedback on "
        "what needs to be improved."
    )
    messages = [
        {"role": "system", "content": "You are a code evaluation agent."},
        {"role": "user", "content": prompt}
    ]
    response = call_chat_completion(model="gpt-4o-mini", messages=messages, temperature=0.3)
    evaluation = response.choices[0].message.content
    return evaluation

def main():
    # Prompt user for custom input
    print("Enter the source code (press Enter on an empty line to finish):")
    source_code_lines = []
    while True:
        line = input()
        if line == "":
            break
        source_code_lines.append(line)
    source_code = "\n".join(source_code_lines)

    source_lang = input("Enter the source language (e.g., Python): ").strip()
    target_lang = input("Enter the target language (e.g., JavaScript): ").strip()
    test_input = input("Enter test input for the converted code (leave blank if not needed): ").strip()
    ideal_output = input("Enter the ideal output for the given test input: ").strip()

    print("\n=== Invoking Planner Agent ===")
    plan = planner_agent(source_code, source_lang, target_lang)
    print("Planner Agent Output:")
    print(plan)

    max_attempts = 5  # Avoid infinite loop if conversion repeatedly fails.
    attempt = 0
    feedback_context = ""
    final_converted_code = None

    while attempt < max_attempts:
        print(f"\n=== Attempt {attempt + 1}: Invoking Converter Agent ===")
        converted_code = converter_agent(plan, source_code, source_lang, target_lang, feedback_context)
        print("Converter Agent Output:")
        print(converted_code)

        print("\n=== Invoking Evaluator Agent ===")
        evaluation = evaluator_agent(source_code, converted_code, source_lang, target_lang, test_input, ideal_output)
        print("Evaluator Agent Output:")
        print(evaluation)

        # Check if evaluation starts with "PASS:" (indicating success)
        if evaluation.strip().upper().startswith("PASS:"):
            final_converted_code = converted_code
            print("\nConversion successful!")
            break
        else:
            # Use evaluator feedback to refine the conversion.
            feedback_context = evaluation
            print("\nEvaluator did not pass the conversion. Regenerating code using evaluator feedback...")
            attempt += 1

    if final_converted_code:
        print("\n[Final Output] Converted Code:")
        print(final_converted_code)
    else:
        print("\n[Final Output] Conversion failed after maximum attempts. Last evaluation feedback:")
        print(feedback_context)

if __name__ == "__main__":
    main()
