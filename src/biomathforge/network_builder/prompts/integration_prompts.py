# Prompt for integrating formulas
integrate_model_prompt_template = """Create a connected biological reaction network from the provided equations.

**Equations:**
{equations}

**Main Pathways:**
{main_signaling_pathways}

**Expected Readouts:**
{expected_readouts}


**Requirements:**
1. **Connect equations into one continuous network** - add biological reactions to bridge gaps if needed
2. **Focus on main pathways**  
   • Keep equations relevant to pathways/readouts, discard irrelevant ones  
   • For every keyword in *Main Pathways*, also include any synonymous or paralogous molecules present in *Equations* (e.g., other members of the same receptor or kinase family) and connect them into the same signaling stream.
3. **Unify notation** - treat phosphorylation variants as identical (e.g., ERK1_p → ERK_p)
4. **Maintain biological accuracy** - only add well-established biological reactions

**Output:** Reaction equations only, one per line, following system format."""


# Standardize and deduplicate reactions
drop_duplicate_template = """
Standardize and deduplicate these reactions:

**Reactions:**
{raw_reactions}

**Rules:**
• 1x phosphorylated → add "_p" 
• 2x phosphorylated → add "_pp"
• Activated → add "_act"
• Remove state prefixes (u/p/pp)
• Dimers → "A-A" format
• Remove "Sig_" prefix
• Collapse isoforms (AKT1/2/3 → AKT) only if reactions become identical
• Keep one copy of identical reactions, prefer shorter catalyst names

**Output:** Reaction equations only, one per line.
"""

# Rewrite continuity prompt
rewrite_continuity_template = """The following kinetic reaction equations do not form a connected network.

**Equations:**
{equations}

**Subnetworks:**
{subnetworks}

**Main Pathways:**
{main_signaling_pathways}

**Expected Readouts:**
{expected_readouts}


**Task:**
1. Use Subnetwork 1 as the core. Connect other subnetworks by adding biologically meaningful signaling reactions.
2. **Do NOT add reverse reactions.** Add forward reactions (phosphorylation, binding) that create new pathways.
3. Remove irrelevant equations. Unify notation for same molecules.
4. Ensure expected readouts are reachable through connected pathways.

**Output:** Reaction equations only, one per line, following system format."""
