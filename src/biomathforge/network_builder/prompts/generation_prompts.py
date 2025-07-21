# Prompt for generating formulas
generation_prompt_template = """Generate kinetic reaction equations that describe the relationships among the following genes based on the given reaction table. There may be multiple valid equations. Extract the necessary information from the table, identify common reaction patterns, and aggregate redundant expressions. Strictly follow the format specified in the system prompt.

### Genes (Reaction Components):
{genes}

### Guidelines:
- For the "Reaction" in the Reaction Table, infer the reaction type from the rate equation and write the reaction equation in the specified format.
- Convert gene names into their corresponding functional protein names where appropriate (e.g., **ERK**, **PI3K**, **Wnt**).  
- Ensure that the equations reflect biologically meaningful interactions based on the given reaction table.

### Reaction Table:
{reference_tbl}

### Output:
Provide the equations strictly follow the format specified in the system prompt. Each equation should be separated by "\n". Do not include any explanations or additional text."""


# Rewrite prompt
rewrite_prompt_template = """Rewrite the following kinetic reaction equations to ensure that they are biologically meaningful and follow the format specified in the system prompt. Correct any errors, inaccuracies, or inconsistencies in the equations.

### Invalid lines:
{invalid_lines}

### Output:
Provide the equations strictly follow the format specified in the system prompt. Each equation should be separated by "\n". Do not include any explanations or additional text."""