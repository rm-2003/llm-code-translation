# LLM Code Translation

Academic project exploring LLM-based source-code translation with planning, conversion, execution feedback, and evaluation agents.

## Contents

- `test2.py`: OpenAI-based translation pipeline.
- `test2_groq.py`: Groq-based variant.
- `test.py`, `test2_Working.py`, `test2_changes.py`: experimental pipeline versions.
- `Benchmark_wrapper.py`: experimental batch translation and static evaluation utilities.
- `Project_output/`: saved benchmark results, logs, and source/target programs.
- `source_code.txt`: sample input.

## Setup

Use Python 3.12 and create an isolated environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:OPENAI_API_KEY = "your-key"
# For the Groq variant:
$env:GROQ_API_KEY = "your-key"
python test2.py
```

Read the prompts to select source and target languages. The scripts may invoke compilers or execute generated code; run them in an isolated environment with suitable language toolchains installed. API calls may incur charges.

`.env.example` documents the environment variables; configure them in your shell before running.

## Benchmark data and limitations

The original project uses XLCoST. The third-party repository and full datasets are excluded from this upload; obtain them separately and follow their licensing terms. `Benchmark_wrapper.py` contains machine-specific paths that must be adjusted before running. Some static metrics are experimental or placeholders, including XLCoST scoring and the data-flow proxy. Saved benchmark results are historical outputs, not a guarantee of current API/model behavior.

This repository is a clean snapshot of the supplied project and results. Virtual environments, editor files, credentials, full external datasets, and the original Git history are excluded.
