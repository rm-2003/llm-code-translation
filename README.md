# LLM Code Translation

Academic project exploring LLM-based source-code translation with planning, conversion, execution feedback, and evaluation agents.

## At a glance

| Item | Overview |
| --- | --- |
| Goal | Translate source code between programming languages with LLM agents and feedback |
| Approach | Planning, code generation, compilation/execution feedback, and LLM evaluation |
| API variants | OpenAI pipeline and a Groq variant |
| Languages in saved results | C, C++, C#, Java, JavaScript, PHP, Python |
| Benchmark coverage | 160 translation records across 16 directed language pairs; 10 programs per direction |
| Project status | Academic prototype with saved benchmark outputs and experimental evaluation utilities |

[Results](#results) · [How it works](#how-it-works) · [Setup](#setup) · [Saved artifacts](#saved-artifacts) · [Limitations](#benchmark-data-and-limitations)

## Results

The saved benchmark covers **160 translation records across 7 languages**. The following means are calculated from all records in [detailed_benchmark_results.json](Project_output/detailed_benchmark_results.json), with equal weight per record.

| Reported metric | Overall mean |
| --- | ---: |
| AST similarity | 0.7110 |
| CodeBERT similarity | 0.9714 |
| Dataflow similarity | 0.5872 |

These are similarity scores on a 0–1 scale, **not translation accuracy or execution pass rates**. The artifacts do not establish a functional-correctness rate. Metric implementation and reproducibility limitations are described below.

### Highlights

- **Python → Java** has the highest mean reported AST similarity (**0.8228**) and dataflow similarity (**0.6466**).
- **C → PHP** has the highest mean reported CodeBERT similarity (**0.9797**).
- Each direction contains only **10 programs**, so these comparisons describe this saved sample rather than general language-pair performance.

<details>
<summary>View all 16 translation directions</summary>

Values below are the per-direction averages in [benchmark_results.csv](Project_output/benchmark_results.csv).

| Translation direction | Programs | AST similarity | CodeBERT similarity | Dataflow similarity |
| --- | ---: | ---: | ---: | ---: |
| C# → C | 10 | 0.6646 | 0.9688 | 0.5693 |
| C# → C++ | 10 | 0.6250 | 0.9761 | 0.5611 |
| C++ → C# | 10 | 0.7398 | 0.9630 | 0.6259 |
| C++ → Python | 10 | 0.6429 | 0.9765 | 0.5101 |
| C → C# | 10 | 0.7004 | 0.9648 | 0.5964 |
| C → JavaScript | 10 | 0.6431 | 0.9713 | 0.5625 |
| C → PHP | 10 | 0.7688 | 0.9797 | 0.6273 |
| Java → JavaScript | 10 | 0.6451 | 0.9669 | 0.5921 |
| Java → PHP | 10 | 0.6813 | 0.9776 | 0.5649 |
| Java → Python | 10 | 0.6690 | 0.9761 | 0.5360 |
| JavaScript → C | 10 | 0.7548 | 0.9737 | 0.6014 |
| JavaScript → Java | 10 | 0.7502 | 0.9639 | 0.6083 |
| PHP → C | 10 | 0.7879 | 0.9703 | 0.6300 |
| PHP → Java | 10 | 0.7687 | 0.9759 | 0.5863 |
| Python → C++ | 10 | 0.7114 | 0.9768 | 0.5772 |
| Python → Java | 10 | 0.8228 | 0.9614 | 0.6466 |

</details>

## How it works

1. **Plan:** a planner agent outlines how to translate the input program.
2. **Translate:** a converter agent generates code in the target language.
3. **Check:** the pipeline attempts compilation/execution and checks available test inputs and outputs.
4. **Refine:** execution feedback or an evaluator LLM guides further conversion attempts when needed.
5. **Record:** benchmark artifacts store generated code, references, and similarity metrics.

The OpenAI implementation in `test2.py` configures its agent calls with `gpt-4o-mini`. This is a source-code setting; it does not independently establish the model used for every historical benchmark record.

## Saved artifacts

| Artifact | What it contains |
| --- | --- |
| [CSV results](Project_output/benchmark_results.csv) | Mean, minimum, maximum, and program count for each translation direction |
| [Excel results](Project_output/benchmark_results_excel.xlsx) | Saved spreadsheet report |
| [Detailed JSON](Project_output/detailed_benchmark_results.json) | 160 records with source, generated and reference code, and metrics |
| [Compact JSON](Project_output/benchmark_results.json) | A smaller 16-record artifact; this is not the full 160-record dataset |
| [Benchmark log](Project_output/benchmark_log_20250510_001532.txt) | Historical run log |

The `split_src_programs/` and `split_target_programs/` folders are empty placeholders in the supplied output folder.

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
