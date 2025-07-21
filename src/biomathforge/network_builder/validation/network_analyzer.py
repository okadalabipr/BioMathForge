import re
import pandas as pd
from typing import List, Optional

from biomathforge.shared.utils.logger import BioMathForgeLogger


def parse_reaction_line(line: str, idx: int, logger: Optional[BioMathForgeLogger] = None) -> Optional[List[dict]]:
    """
    Parses a single reaction line and returns a list of edge dictionaries.
    Each dictionary has the format: { "from": ..., "to": ..., "relation": ..., "parameters": ... }.
    If there are two reactants or two products, a dummy node " " is used to split the edge.
    """
    logger = logger or BioMathForgeLogger("reaction_parser")

    # 1. Extract parameters (if any) after the "|" separator.
    if "|" in line:
        reaction_text, param_text = line.split("|", 1)
        parameters = param_text.strip()
    else:
        reaction_text = line
        parameters = ""
    reaction_text = reaction_text.strip()
    
    # 2. Determine the reaction type (relation) using the keywords from the reference table.    
    if re.search(r'\bdimerizes\b', reaction_text):
        relation = "dimerize"
    elif re.search(r'\bbinds\b', reaction_text):
        relation = "bind"
    elif re.search(r'\bdissociates\b', reaction_text):
        relation = "dissociate"
    elif re.search(r'\bdephosphorylates\b', reaction_text):
        relation = "dephosphorylate"
    elif re.search(r'\bphosphorylates\b', reaction_text):
        relation = "phosphorylate"
    elif re.search(r'\bis phosphorylated\b', reaction_text):
        relation = "is phosphorylated"
    elif re.search(r'\bis dephosphorylated\b', reaction_text):
        relation = "is dephosphorylated"
    elif re.search(r'\btranscribes\b', reaction_text):
        relation = "transcribe"
    elif re.search(r'\bsynthesizes\b', reaction_text):
        relation = "synthesize"
    elif re.search(r'\bis synthesized\b', reaction_text):
        relation = "is synthesized"
    elif re.search(r'\bdegrades\b', reaction_text):
        relation = "degrade"
    elif re.search(r'\bis degraded\b', reaction_text):
        relation = "is degraded"
    elif re.search(r'\btranslocates\b|\btranslocated\b', reaction_text):
        relation = "translocate"
    elif re.search(r'\bactivates\b', reaction_text):
        relation = "activate"
    elif re.search(r'\binhibits\b', reaction_text):
        relation = "inhibit"
    else:
        # If arrow notation is present, consider it a state transition.
        if "<-->" in reaction_text or "-->" in reaction_text:
            relation = "state transition"
        else:
            relation = "unknown"
            logger.info(f"Unknown reaction encountered: {reaction_text}")
            return None
    
    # 3. Extract the reactants and products by splitting on arrows or keywords.
    left = right = ""
    if "<-->" in reaction_text:
        parts = reaction_text.split("<-->")
        left, right = parts[0].strip(), parts[1].strip()
    elif "-->" in reaction_text:
        parts = reaction_text.split("-->")
        left, right = parts[0].strip(), parts[1].strip()
    elif "dissociates to" in reaction_text:
        parts = reaction_text.split("dissociates to")
        left, right = parts[0].strip(), parts[1].strip()
    else:
        # If no arrow is found, split using the reaction verb.
        if relation in ["transcribe", "synthesize", "degrade", "activate", "inhibit"]:
            verb = {
                "transcribe": "transcribes",
                "synthesize": "synthesizes",
                "degrade": "degrades",
                "activate": "activates",
                "inhibit": "inhibits"
            }[relation]
            parts = reaction_text.split(verb)
            left, right = parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
        elif relation == "is synthesized":
            # Example: "A is synthesized": product is A (no reactant specified)
            left = f"r{idx}"
            right = reaction_text.split("is")[0].strip()
        elif relation == "is degraded":
            # Example: "A is degraded": reactant is A (no product specified)
            left = reaction_text.split("is")[0].strip()
            right = f"r{idx}"
        else:
            # Fallback: use the first and last token.
            logger.info(f"Fallback splitting used: reaction_text='{reaction_text}', left='{left}', right='{right}'")
            return None
    
    # 4. Further extract reactants and products based on the reaction type.
    reactants = []
    products = []
    
    if relation in ["bind", "phosphorylate", "dephosphorylate"]:
        # Example: "EGF binds ErbB1" or "B phosphorylates uA"
        verb = {
            "bind": "binds",
            "phosphorylate": "phosphorylates",
            "dephosphorylate": "dephosphorylates"
        }[relation]
        parts = left.split(verb)
        reactants = [p.strip() for p in parts if p.strip()]
        products = [right]
    elif relation in ["is phosphorylated", "is dephosphorylated"]:
        # Example: "EGFR_Shc is phosphorylated" → reactant: "EGFR_Shc"
        verb = "is phosphorylated" if relation == "is phosphorylated" else "is dephosphorylated"
        parts = left.split(verb)
        reactants = [parts[0].strip()] if parts[0].strip() else []
        products = [right]
    elif relation == "dissociate":
        # Example: "A-B dissociates to A and B"
        reactants = [left]
        # If the right part contains "and", split it to get multiple products.
        if "and" in right:
            products = [p.strip() for p in right.split("and")]
        else:
            products = [right]
    elif relation == "dimerize":
        # Example: "A dimerizes <--> A-A"
        m = re.search(r"(\S+)\s*dimerize", reaction_text)
        if m:
            reactants = [m.group(1)]
        else:
            reactants = [left]
        products = [right]
    elif relation == "translocate":
        # Example: "Acyt translocates <--> Anuc"
        m = re.search(r"^(\S+)\s*(translocates|is translocated)", left)
        if m:
            reactants = [m.group(1)]
        else:
            reactants = [left]
        products = [right]
    elif relation in ["transcribe", "synthesize", "activate", "inhibit"]:
        # Example: "B transcribes A", etc.
        verb = {
            "transcribe": "transcribes",
            "synthesize": "synthesizes",
            "activate": "activates",
            "inhibit": "inhibits"
        }[relation]
        parts = reaction_text.split(verb)
        reactants = [parts[0].strip()]
        products = [parts[1].strip()] if len(parts) > 1 else []
    elif relation == "is synthesized":
        # Example: "A is synthesized" → product is A (no reactant specified)
        reactants = []
        products = [right]
    elif relation == "is degraded":
        # Example: "A is degraded" → reactant is A (no product specified)
        reactants = [left]
        products = []
    elif relation == "degrade":
        # Example: "B degrades A"
        verb = "degrades"
        parts = reaction_text.split(verb)
        reactants = [parts[0].strip()]
        products = [parts[1].strip()] if len(parts) > 1 else []
    elif relation == "state transition":
        # Example: "A <--> B"
        reactants = [left]
        products = [right]
    else:
        # Fallback: use left and right as reactants and products.
        reactants = [left] if left else []
        products = [right] if right else []
        logger.info(f"Using fallback for reactants and products: reaction_text='{reaction_text}', left='{left}', right='{right}'")
    
    # 5. Create rows for the DataFrame according to the rules for multiple reactants/products.
    rows = []
    if len(reactants) == 1 and len(products) == 1:
        # Simple case: one reactant and one product.
        rows.append({
            "from": reactants[0],
            "to": products[0],
            "relation": relation,
            "parameters": parameters
        })
    elif len(reactants) == 2 and len(products) == 1:
        # Two reactants: create two edges from each reactant to a dummy node,
        # then one edge from the dummy node to the product.
        if relation == "bind":
            rows.append({
                "from": reactants[0],
                "to": f"r{idx}",
                "relation": relation,
                "parameters": parameters
            })
            rows.append({
                "from": reactants[1],
                "to": f"r{idx}",
                "relation": relation,
                "parameters": parameters
            })
            rows.append({
                "from": f"r{idx}",
                "to": products[0],
                "relation": relation,
                "parameters": parameters
            })
        else:
            # phosphorylation, dephosphorylation
            rows.append({
                "from": reactants[0],
                "to": reactants[1],
                "relation": relation,
                "parameters": parameters
            })
            rows.append({
                "from": reactants[1],
                "to": products[0],
                "relation": "is phosphorylated" if relation == "phosphorylate" else "is dephosphorylated",
                "parameters": parameters
            })
    elif len(reactants) == 1 and len(products) == 2:
        # Two products: create one edge from the reactant to a dummy node,
        # then two edges from the dummy node to each product.
        # This should be 'dissociate'
        rows.append({
            "from": reactants[0],
            "to": products[0],
            "relation": relation,
            "parameters": parameters
        })
        rows.append({
            "from": reactants[0],
            "to": products[1],
            "relation": relation,
            "parameters": parameters
        })
    elif len(reactants) == 2 and len(products) == 2:
        # Two reactants and two products: create edges from each reactant to a dummy node,
        # and from the dummy node to each product.
        for r in reactants:
            rows.append({
                "from": r,
                "to": f"r{idx}",
                "relation": relation,
                "parameters": parameters
            })
        for p in products:
            rows.append({
                "from": f"r{idx}",
                "to": p,
                "relation": relation,
                "parameters": parameters
            })
    else:
        # If the number of reactants or products is unclear, use the left and right parts directly.
        rows.append({
            "from": left,
            "to": right,
            "relation": relation,
            "parameters": parameters
        })

    return rows


def parse_lines_to_dataframe(reaction_lines: List[str], logger: Optional[BioMathForgeLogger] = None) -> pd.DataFrame:
    """
    Convert a list of reaction lines into a network graph (DataFrame).

    Args:
        reaction_lines: List of reaction strings
        logger: Optional logger instance

    Returns:
        pd.DataFrame: DataFrame with columns [from, to, relation, parameters]
    """
    logger = logger or BioMathForgeLogger("reaction_parser")
    all_rows = []
    for idx, line in enumerate(reaction_lines):
        parsed = parse_reaction_line(line, idx, logger=logger)
        if parsed:
            all_rows.extend(parsed)
    return pd.DataFrame(all_rows, columns=["from", "to", "relation", "parameters"])
