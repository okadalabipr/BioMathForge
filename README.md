# BioMathForge

**Integrated Biochemical Reaction Network Generation and Pathway Analysis Toolkit**

BioMathForge is a comprehensive toolkit for generating, integrating, and analyzing biochemical reaction networks. It combines AI-powered reaction network generation with advanced pathway analysis to provide insights into biological systems.

This toolkit is associated with the study: **Tsutsui M et al., 2025. *****Literature-derived, context-aware gene regulatory networks improve biological predictions and mathematical modeling*****.**

<img width="3927" height="2145" alt="fig6" src="https://github.com/user-attachments/assets/7414a985-affb-46f2-a0bd-b6ee6daadf47" />

---

## Features

### 🧬 Network Generation

- AI-powered generation of reaction equations from biological inputs
- Automatic validation and integration of reactions into coherent networks
- Mass balance enforcement and divergence prevention for robust simulations

### 🔍 Pathway Analysis

- Web-enhanced pathway inference using search-driven techniques
- Prediction and prioritization of expected readouts
- Graph-based modeling and analysis via LangGraph workflow

---

## Quick Start

### 1. Installation

```bash
git clone https://github.com/okadalabipr/BioMathForge
cd BioMathForge
pip install .

cp .env.example .env
# Edit `.env` and insert your valid API KEYs
```

---

### 2. Demonstration: MCF-7 Breast Cancer Cell Line

We provide an example workflow using breast cancer-related equations curated from BioModels. These are located under `examples/mcf-7`.

#### Step 0. Prepare Input Equations

Small-scale example equations (`example_biomodels_equations.csv`) derived from BioModels are provided. Full datasets and details are described in our accompanying paper and the repository [okadalabipr/context-dependent-GRN](https://github.com/okadalabipr/context-dependent-GRN).

---

#### Step 1. Generate Formatted Reactions

Convert raw equations to a standardized format using the `generate_formatted_reactions` function.

```python
from dotenv import load_dotenv
load_dotenv()

from biomathforge import generate_formatted_reactions
import pandas as pd

biomodels_reactions = pd.read_csv("examples/mcf-7/example_biomodels_equations.csv")
validated_reactions = generate_formatted_reactions(biomodels_reactions)
```

📄 Output: `examples/mcf-7/generated_formula.txt`

---

#### Step 2. Analyze Pathways with Web Search

Use web-based research to identify key signaling pathways and expected readouts under experimental conditions.

```python
from biomathforge import run_pathway_analysis

report = run_pathway_analysis(
    reactions_path="examples/mcf-7/generated_formula.txt",
    condition_path="examples/mcf-7/experimental_condition.txt"
)
```

📄 Output: `examples/mcf-7/pathway_analysis_result.json`

---

#### Step 3. Integrate Reactions

Integrate the equations into a complete network using biological constraints and inferred readouts.

```python
from biomathforge import integrate_reactions

equations = [eq.strip() for eq in open("examples/mcf-7/generated_formula.txt") if eq.strip()]
integrated_equations, source_nodes, sink_nodes = integrate_reactions(equations, report)
```

📄 Outputs:

- `examples/mcf-7/integrated_equations_final.txt`
- `examples/mcf-7/terminal_nodes.json`

---

#### Step 4. Enhance Feedback and Crosstalk

Add plausible feedback loops and crosstalk reactions to improve biological realism.

```python
from biomathforge import run_enhance_feedback_crosstalk

report, enhancement_summary, added_reactions = run_enhance_feedback_crosstalk(
    reactions_path="examples/mcf-7/integrated_equations_final.txt",
    terminal_nodes_path="examples/mcf-7/terminal_nodes.json",
    reactions_overviews_path="examples/mcf-7/pathway_analysis_result.json"
)
equations = report.split("\n")
```

📄 Output: `examples/mcf-7/breast_cancer_reactions.txt`

---

#### Step 5. Finalize the Model

Clean up, deduplicate, and finalize the set of reactions for downstream use (e.g., simulation or export).

```python
from biomathforge import finalize_reactions

finalized_equations = finalize_reactions(equations)
```

📄 Output: `examples/mcf-7/breast_cancer_reactions_finalized.txt`

---

## 🔧 Requirements

- Python 3.10+
- OpenAI API key (or other supported LLM providers)
- TAVILY API key for web-enhanced pathway analysis (or other supported web search APIs)

---

## 📄 License

This project is licensed under the MIT License.

---

## 🧑‍💼 Citation

If you use BioMathForge in your research, please cite our accompanying paper (coming soon) and reference this repository.

