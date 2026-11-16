from pathlib import Path
import json
import csv
import subprocess
from typing import List, Dict

# Static Evaluation Utilities: AST, CodeBERT, Data Flow, XLCoST (framework only)
import ast
import difflib
import torch
from transformers import RobertaTokenizer, RobertaModel
from typing import Tuple
from sklearn.metrics.pairwise import cosine_similarity
import os
import re

def split_programs(file_path: Path, output_dir: Path, extension=".c"):
    """
    Splits a tokenized file into multiple programs by newline, and saves them as separate files.
    Each line is assumed to be a full program.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    with open(file_path, 'r', encoding='utf-8') as f:
        programs = f.read().strip().split('\n')

    for idx, program in enumerate(programs):
        output_file = output_dir / f'program_{idx + 1}{extension}'
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(program)

    return len(programs)

from pathlib import Path

def get_program_pairs(source_dir: Path, target_dir: Path, max_samples: int = 2) -> List[Dict]:
    """Get aligned source-target program pairs from given directories."""
    source_files = sorted(source_dir.glob("*.c"))
    target_files = sorted(target_dir.glob("*.cpp"))
    pairs = []

    for i in range(min(max_samples, len(source_files))):
        with open(source_files[i], "r", encoding="utf-8") as f_src, \
             open(target_files[i], "r", encoding="utf-8") as f_tgt:
            source_code = f_src.read()
            target_code = f_tgt.read()
            pairs.append({
                "index": i,
                "source_code": source_code,
                "target_code": target_code
            })

    return pairs

def run_test2_translation(source_code: str, source_lang: str, target_lang: str) -> str:
    """
    Writes source_code to source_code.txt and invokes test2.py for translation.
    Captures stdout from the script.
    """
    source_code = source_code.replace("NEW_LINE", "\n")
    source_file = Path("source_code.txt")
    source_file.write_text(source_code, encoding="utf-8")

    try:
        result = subprocess.run(
            ["python3", "C:/Users/RISHABH/Desktop/Acads_BITS/4-2/Intro_to_LLMs/LLM_Project/test2.py"],
            input=f"{source_lang}\n{target_lang}\nno\n",  # simulates CLI input
            text=True,
            capture_output=True,
            timeout=300
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return "Error: Translation timed out."
    except Exception as e:
        return f"Error: {str(e)}"

def batch_translate_and_collect(
    program_pairs: List[Dict], source_lang: str, target_lang: str,
    csv_path: Path, json_path: Path
) -> None:
    results = []

    for pair in program_pairs:
        idx = pair['index']
        print(f"\n=== Translating Program {idx + 1} ===")
        source = pair['source_code']
        reference = pair['target_code']

        output = run_test2_translation(source, source_lang, target_lang)
        output_preview = output[:1000] + ("..." if len(output) > 1000 else "")

        results.append({
            "index": idx,
            "source_code": source[:500],
            "reference_code": reference[:500],
            "translation_output": output_preview
        })

        print(f"✓ Translated Program {idx + 1}:\n{output_preview[:300]}...\n")

    # Save to CSV
    with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Save to JSON
    with open(json_path, "w", encoding="utf-8") as jsonfile:
        json.dump(results, jsonfile, indent=2)

    print(f"\n✅ Results saved to:\n- CSV: {csv_path}\n- JSON: {json_path}")



# num_c, num_cpp

# # Get aligned C → C++ program pairs
# program_pairs = get_program_pairs(source_dir, target_dir, max_samples=5)
# program_pairs[0]  # Preview first pair

# # Example usage — assumes `program_pairs` is already prepared
# csv_out = Path("/mnt/data/translation_results.csv")
# json_out = Path("/mnt/data/translation_results.json")

# batch_translate_and_collect(
#     program_pairs=program_pairs,
#     source_lang="C",
#     target_lang="C++",
#     csv_path=csv_out,
#     json_path=json_out
# )

def get_program_pairs_generic(
    source_dir: Path, target_dir: Path, source_ext: str, target_ext: str, max_samples: int = 5
) -> List[Dict]:
    """
    Gets aligned source-target program pairs based on file extension and order in directory.
    """
    source_files = sorted(source_dir.glob(f"*{source_ext}"))
    target_files = sorted(target_dir.glob(f"*{target_ext}"))
    pairs = []

    for i in range(min(max_samples, len(source_files), len(target_files))):
        with open(source_files[i], "r", encoding="utf-8") as f_src, \
             open(target_files[i], "r", encoding="utf-8") as f_tgt:
            source_code = f_src.read()
            target_code = f_tgt.read()
            pairs.append({
                "index": i,
                "source_code": source_code,
                "target_code": target_code,
                "source_file": source_files[i].name,
                "target_file": target_files[i].name
            })

    return pairs

# Language extension mapping
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "java": ".java",
    "javascript": ".js",
    "c#": ".cs",
    "c++": ".cpp",
    "cpp": ".cpp",
    "c": ".c",
    "php": ".php"
}

def prepare_and_run_batch_translation(
    source_lang: str,
    target_lang: str,
    source_dir: Path,
    target_dir: Path,
    sample_count: int = 5
):
    """
    Automatically determines extensions and runs translation for supported languages.
    """
    # Normalize language keys
    source_key = source_lang.strip().lower()
    target_key = target_lang.strip().lower()

    # Validate
    if source_key not in LANGUAGE_EXTENSIONS or target_key not in LANGUAGE_EXTENSIONS:
        raise ValueError(f"Unsupported languages. Supported languages are: {list(LANGUAGE_EXTENSIONS.keys())}")

    source_ext = LANGUAGE_EXTENSIONS[source_key]
    target_ext = LANGUAGE_EXTENSIONS[target_key]

    # Output paths
    csv_path = Path(f"/mnt/data/{source_key}_to_{target_key}_results.csv")
    json_path = Path(f"/mnt/data/{source_key}_to_{target_key}_results.json")

    # Load aligned source-target code
    program_pairs = get_program_pairs_generic(
        source_dir=source_dir,
        target_dir=target_dir,
        source_ext=source_ext,
        target_ext=target_ext,
        max_samples=sample_count
    )

    # Run translation + collection
    batch_translate_and_collect(
        program_pairs=program_pairs,
        source_lang=source_lang,
        target_lang=target_lang,
        csv_path=csv_path,
        json_path=json_path
    )

    return csv_path, json_path

def compute_ast_tree_distance(code1: str, code2: str) -> float:
    """
    Computes a syntactic similarity score using AST node comparison.
    This simplistic version compares Python code via AST.
    """
    try:
        tree1 = ast.dump(ast.parse(code1))
        tree2 = ast.dump(ast.parse(code2))
        matcher = difflib.SequenceMatcher(None, tree1, tree2)
        return matcher.ratio()  # returns value between 0 and 1
    except Exception:
        return 0.0


def compute_codebert_similarity(code1: str, code2: str) -> float:
    """
    Computes semantic similarity using CodeBERT embeddings.
    """
    tokenizer = RobertaTokenizer.from_pretrained("microsoft/codebert-base")
    model = RobertaModel.from_pretrained("microsoft/codebert-base")

    inputs = tokenizer([code1, code2], padding=True, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state[:, 0, :]  # [CLS] token embeddings

    score = cosine_similarity(embeddings[0].unsqueeze(0), embeddings[1].unsqueeze(0))[0][0]
    return float(score)


def compute_dataflow_similarity(code1: str, code2: str) -> float:
    """
    Stub for DFG similarity. Full implementation depends on language-specific analyzers.
    Currently, compares variable names as a proxy.
    """
    var_pattern = r'\b[_a-zA-Z][_a-zA-Z0-9]*\b'
    vars1 = set(re.findall(var_pattern, code1))
    vars2 = set(re.findall(var_pattern, code2))
    if not vars1 or not vars2:
        return 0.0
    intersection = len(vars1 & vars2)
    union = len(vars1 | vars2)
    return intersection / union


def compute_xlcost_score(source_code: str, generated_code: str, xlcost_folder: Path) -> float:
    """
    Placeholder function: should call XLCoST repo's retrieval-based scoring function.
    """
    # This is a stub for now.
    return -1  # Replace with actual score after integration


def evaluate_all_static_metrics(
    source_code: str,
    generated_code: str,
    reference_code: str,
    lang: str,
    xlcost_path: Path = Path("/mnt/data/XLCoST")
) -> dict:
    """
    Computes all static evaluation metrics and returns them in a dictionary.
    """
    return {
        "AST_similarity": compute_ast_tree_distance(generated_code, reference_code) if lang.lower() == "python" else -1,
        "CodeBERT_similarity": compute_codebert_similarity(generated_code, reference_code),
        "DFG_similarity": compute_dataflow_similarity(generated_code, reference_code),
        "XLCoST_score": compute_xlcost_score(source_code, generated_code, xlcost_path)
    }


src_path = Path("'C:/Users/RISHABH/Desktop/Acads_BITS/4-2/Intro_to_LLMs/LLM_Project/XLCoST_data/generation/pair_data_tok_full/C++-C/test-C++-C-tok.c'")
target_path = Path("'C:/Users/RISHABH/Desktop/Acads_BITS/4-2/Intro_to_LLMs/LLM_Project/XLCoST_data/generation/pair_data_tok_full/C++-C/test-C++-C-tok.cpp'")

source_dir = Path("C:/Users/RISHABH/Desktop/Acads_BITS/4-2/Intro_to_LLMs/LLM_Project/split_src_programs")
target_dir = Path("C:/Users/RISHABH/Desktop/Acads_BITS/4-2/Intro_to_LLMs/LLM_Project/split_target_programs")

num_c = split_programs(src_path, source_dir, ".c")
num_cpp = split_programs(target_path, target_dir, ".cpp")

prepare_and_run_batch_translation(
    source_lang="C",
    target_lang="Cpp",
    source_dir=source_dir,
    target_dir=target_dir,
    sample_count=2
)
