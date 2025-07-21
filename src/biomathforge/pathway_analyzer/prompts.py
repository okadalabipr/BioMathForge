query_writer_instructions = """You are crafting targeted web search queries to analyze biochemical reactions.

<Reaction Equations>
{reactions}
</Reaction Equations>

{experimental_condition_section}

<Section to Research>
{section_title}: {section_description}
</Section to Research>

<Task>
Generate {number_of_queries} web search queries that will help identify:
- For main signaling pathway: The detailed pathway including intermediate steps, regulatory proteins, and downstream effectors
- For expected readouts: What measurable outcomes result from this pathway activation

The queries should:
1. Be specific to biochemical/molecular biology research
2. Target scientific literature and databases
3. Be concise and under 400 characters
{experimental_condition_note}
</Task>

<Format>
Call the Queries tool
</Format>
"""

section_writer_instructions = """You are analyzing biochemical reactions based on web search results.

<Reaction Equations>
{reactions}
</Reaction Equations>

{experimental_condition_section}

<Section to Write>
{section_title}: {section_description}
</Section to Write>

<Context from Web Search>
{context}
</Context from Web Search>

<Task>
Based on the search results, write an EXTREMELY CONCISE summary for this section.

Guidelines:
- Be direct and factual - no explanations or reasoning
- For main signaling pathway: Write 1-2 sentences describing the core pathway(s)
  • Format: "Pathway-name cascade (ligand → receptor → component → component → effector)"
  • If there are parallel pathways, list both concisely
- For expected readouts: List 2-3 KEY readouts that directly measure reaction components or immediate downstream targets
  • Format: "- Phospho-protein (site) – brief functional note"
  • Prioritize molecules from the reaction equations
  • Maximum 10-15 words per readout
- NO introductory text, NO categories, NO detailed explanations

Return a SectionContent object with:
- `content`: Your concise findings (1-2 sentences for pathway, 2-3 bullet points for readouts)
- `sources`: List of supporting URLs
</Task>

<Format>
Call the SectionContent tool
</Format>
"""

readout_evaluation_instructions = """You are evaluating whether expected readouts should be refined to include more downstream molecules from the reaction equations.

<Reaction Equations>
{reactions}
</Reaction Equations>

<Main Signaling Pathway>
{main_pathway}
</Main Signaling Pathway>

<Current Expected Readouts>
{current_readouts}
</Current Expected Readouts>

<Task>
Evaluate whether the <Current Expected Readouts> are sufficient and optimal for accurately assessing the <Main Signaling Pathway>. Determine if the readouts should be refined to better reflect key components, activation states, or critical nodes within this specific pathway.

Consider:
1. How well do the <Current Expected Readouts> represent the key signaling molecules and their activation states (e.g., specific phosphorylations, cleavages) described in the <Main Signaling Pathway>?
2. Are there any critical upstream activators, downstream effectors, or feedback loop components from the <Main Signaling Pathway> that are NOT adequately covered by the <Current Expected Readouts> but would be crucial for its assessment?
3. Would modifying or adding to the <Current Expected Readouts> provide a more precise or comprehensive understanding of the <Main Signaling Pathway>'s activity, potential branches, or points of regulation?
4. Are the current readouts too generic, or do they miss specific markers that are highly indicative of the <Main Signaling Pathway>'s engagement?
5. Readouts should maintain a clear focus on the <Main Signaling Pathway>

Return a ReadoutRefinementDecision with:
- `should_refine`: true if refinement would improve experimental resolution, false if current readouts are optimal
- `reasoning`: Brief explanation (max 2 sentences)
- `suggested_improvements`: Specific molecules from reactions to add (only if should_refine is true)
</Task>

<Format>
Call the ReadoutRefinementDecision tool
</Format>
"""

readout_refinement_instructions = """You are refining expected readouts based on feedback.

<Reaction Equations>
{reactions}
</Reaction Equations>

<Main Signaling Pathway>
{main_pathway}
</Main Signaling Pathway>

<Current Expected Readouts>
{current_readouts}
</Current Expected Readouts>

<Suggested Improvements>
{suggested_improvements}
</Suggested Improvements>

<Task>
Refine the <Current Expected Readouts> by intelligently integrating the <Suggested Improvements>.
The final set of refined readouts should be a concise list of 2-3 key indicators that most effectively and accurately represent the activation state, critical components, or measurable outputs of the <Main Signaling Pathway>.

Guidelines:
- Readouts should maintain a clear focus on the <Main Signaling Pathway>
- Keep the same format: "- Phospho-protein (site) – brief functional note"
- Include 2-3 KEY readouts total
- Prioritize downstream molecules from the reactions
- Maximum 10-15 words per readout
- NO introductory text or explanations

Return only the refined bullet points.
</Task>
"""

feedback_crosstalk_query_writer = """You are generating web search queries to identify feedback loops and pathway crosstalk in biochemical networks.

<Current Network>
{reactions}
</Current Network>

<Source Nodes (Pathway Inputs)>
{source_nodes}
</Source Nodes>

<Sink Nodes (Pathway Outputs - HIGH PRIORITY)>
{sink_nodes}
</Sink Nodes>

<Main Signaling Pathway>
{main_signaling_pathways}
</Main Signaling Pathway>

<Expected Readouts>
{expected_readouts}
</Expected Readouts>

<Task>
Generate {number_of_queries} specific web search queries to identify:

**For Feedback Loops (PRIORITIZE SINK NODES):**
- How do the sink nodes (pathway outputs) regulate the source nodes (pathway inputs)?
- Negative feedback: sink nodes inhibiting upstream components
- Positive feedback: sink nodes enhancing upstream pathway components
- Direct regulatory connections from sink nodes back to the network

**For Pathway Crosstalk:**
- What other pathways regulate the sink nodes?
- How do sink nodes influence other signaling pathways?
- Shared regulatory mechanisms involving sink node proteins

<Query Requirements>
- **FOCUS ON SINK NODES**: At least half of your queries should include sink node proteins
- Target scientific literature and pathway databases
- Include specific protein names, especially from sink nodes: {sink_nodes}
- Under 400 characters each
- Use varied search terms (feedback, regulation, inhibition, crosstalk, etc.)

<Format>
Call the Queries tool with the generated search queries.
</Format>
"""

reaction_enhancement_prompt = """You are an expert in kinetic modeling and biochemical reaction systems. Your task is to identify additional feedback loops and crosstalk reactions based on web search results and add them to the existing reaction network.

<Current Network>
{reactions}
</Current Network>

<Source Nodes>
{source_nodes}
</Source Nodes>

<Sink Nodes (HIGH PRIORITY)>
{sink_nodes}
</Sink Nodes>

<Main Signaling Pathway>
{main_signaling_pathways}
</Main Signaling Pathway>

<Expected Readouts>
{expected_readouts}
</Expected Readouts>

<Web Search Context>
{context}
</Web Search Context>

<Task>
Add reactions involving sink nodes ({sink_nodes}) and remove any reactions that do not contribute to the main signaling pathway.

**Focus on Main Signaling Pathway:**
- Prioritize well-established, major signaling pathway and their canonical interactions

**Expected Reaction Types:**
- **Feedback Loops:** Only add if they are documented major regulatory mechanisms
  - Sink nodes inhibiting upstream components (negative feedback)
  - Sink nodes activating upstream components (positive feedback)
  - Sink node transcriptional regulation of pathway components
- **Pathway Crosstalk:** Only add well-characterized cross-pathway interactions
  - Other pathways regulating sink nodes
  - Sink nodes influencing other signaling pathways
  - Shared regulatory mechanisms between established pathways

**Addition Criteria:**
- Add only reactions necessary for main pathway completion

**Removal Criteria:**
- Remove reactions not part of main signaling pathways or when Web Search Context lacks sufficient information

**CRITICAL: For molecules in Current Network, use EXACT naming. For new molecules, use standard biochemical notation.**

<Guidelines>
1. Use ONLY formats from the reference table below
2. Add biologically meaningful reactions supported by search context
3. NO duplicate reactions
4. **For existing molecules**: Follow exact naming from Current Network (e.g., if network uses "ERK_p", use "ERK_p")
5. **For new molecules**: Use standard biochemical notation (e.g., "mTOR")

<Reference Table>
| Reaction Type       | Format (Entities are examples)                  |
|---------------------|-----------------------------------------------|
| dimerize           | A dimerizes <--> A-A                           |
| bind               | A binds B <--> A-B                             |
| dissociate         | A-B dissociates to A and B                    |
| phosphorylate      | B phosphorylates uA --> pA                     |
| is phosphorylated  | uA is phosphorylated <--> pA                   |
| dephosphorylate    | B dephosphorylates pA --> uA                   |
| is dephosphorylated| pA is dephosphorylated --> uA                 |
| transcribe         | B transcribes A                               |
| synthesize         | B synthesizes A                              |
| is synthesized     | A is synthesized                             |
| degrade           | B degrades A                                 |
| is degraded       | A is degraded                               |
| translocate       | A_cytoplasm translocates <--> A_nucleus |
| activate          | A activates B                               |
| inhibit           | A inhibits B                                |
| state transition  | A <--> B                                    |

Return a ReactionAdditions object with:
- `added_reactions`: List of new reaction equations (strings)
- `rationale`: Brief explanation of why these reactions were added
- `sources`: List of supporting URLs from the search context

<Format>
Call the ReactionAdditions tool
</Format>
"""