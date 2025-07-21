# Prevent mass balance divergence
prevent_divergence_template = """
# Task: Add missing degradation reactions to keep mass balance in the model.

## Background / Reason
In an ODE-based biochemical model, any species that is produced but never consumed will
accumulate without bound, leading to unrealistic concentration divergence and preventing
steady-state analysis.  A species already has a "sink" if it is (a) dephosphorylated,
(b) dissociates reversibly, or (c) already marked with "is degraded / degrades …".
Every other species that is generated must therefore have an explicit degradation step.

## Step-by-step process:
1. **Find all products**: List every species that appears on the right side of "→"
2. **Check for sinks**: For each product, look for reactions where it:
  - Gets dephosphorylated (loses _P)
  - Dissociates (A_B → A + B)
  - Has explicit degradation ("is degraded")
3. **Add missing degradations**: For species without sinks, add "<Species> is degraded"

## Reaction list
{reactions}

# Output format
Return the full, updated reactions only, one per line, following system format.
"""

# Rewrite reactions related to "activation" and "inhibition"
rewrite_activation_inhibition_template = """
You are a biochemical‐reaction network assistant.
### Task
Transform the reaction list below into a Michaelis–Menten–style reaction network that my simulation engine can read.

### Parameter naming conventions
- **Activation**: V_[Activator]_[Target], K_[Activator]_[Target]
- **Inhibition (direct)**: V_[Inhibitor]i[Target], K_[Target]i
- **Inhibition (competitive)**: V_[Target], K_[Target], Ki_[Inhibitor]

### Processing steps
1. **Scan for activation/inhibition**: Find all lines with "activates" or "inhibits"
2. **Identify affected species**: Extract regulator and target molecules
3. **Generate @rxn conversions**: Apply the templates above
4. **Update remaining reactions**: Change molecule names to _act/_inact forms
5. **Assemble output**: @rxn lines first, then updated reactions

### Detailed rules
1. **Convert every line containing "activates" or "inhibits"**  
  • If the line is "A activates B", treat B as an enzyme-regulated conversion  
    from an inactive to an active form and write:
    ```@rxn  B_inact  -->  B_act : p[V_A_B] * u[A] * u[B_inact] / ( p[K_A_B] + u[B_inact] )```
  • If the line is "A inhibits B", treat it as enzyme-mediated *de-activation*  
    and use either of the two standard inhibition forms (pick one per reaction):
    ```@rxn  B_act  -->  B_inact : p[V_AiB] * u[A] * u[B_act] / ( p[K_Bi] + u[B_act] )```
    – or –
    ```@rxn  B_inact  -->  B_act : p[V_B] * u[B_inact] / ( p[K_B]*(1 + u[A]/p[Ki_A]) + u[B_inact] )```
2. **Rename biomolecules**  
  • Species that can switch states must end in `_act` or `_inact`.  
  • Use `_act` for the active form (e.g., RAS_act) and `_inact` for the inactive form (e.g., RAS_inact).
3. **Remove the original "activates / inhibits" lines** after you have converted them to `@rxn`.
4. **Keep every other reaction line unchanged**, but update any molecule names so they match the new `_act / _inact` convention.
5. **Output** one contiguous plain-text block that first lists all `@rxn …` lines, followed by the remaining reactions.  
  • Do not output explanations, headings, or code fences.  
  • Preserve the original ordering where possible.

### Reaction list
{reactions}

# Output format
Return the full, updated reactions only, one per line.
"""