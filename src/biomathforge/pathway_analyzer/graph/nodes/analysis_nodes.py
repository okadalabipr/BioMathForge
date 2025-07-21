from langchain_core.runnables import RunnableConfig

from biomathforge.pathway_analyzer.state import (ReportState,
                      ExtendedReportState,
                      PathwayAnalysisSection,
                      PathwayAnalysisOutput,
                      FeedbackEnhancementState)

async def generate_sections(state: ReportState, config: RunnableConfig):
    """
    Generates the initial, fixed sections that need to be analyzed.

    This node doesn't call an LLM; it deterministically defines the two main
    research tasks for the graph to perform.
    """
    # Define the two primary sections for the analysis.
    sections = [
        PathwayAnalysisSection(
            section_type="main_signaling_pathway",
            title="Main Signaling Pathway",
            description="Identify the detailed signaling pathway these reactions represent, including all intermediate steps, regulatory proteins, feedback loops, and downstream effectors (e.g., detailed EGFR→RAS→RAF→MEK→ERK cascade with regulatory components)"
        ),
        PathwayAnalysisSection(
            section_type="expected_readouts",
            title="Expected Readouts",
            description="Identify measurable outcomes or downstream effects of this pathway activation"
        )
    ]
    
    # Update the state with the list of sections to be processed.
    return {"sections": sections}

def gather_completed_sections(state: ReportState):
    """
    Aggregates the content from all completed parallel section-writing tasks.

    This node runs after the `build_section_with_web_research` subgraph
    has finished for all sections.
    """
    main_pathway = ""
    expected_readouts = ""
    
    # Iterate through the results from the parallel sub-graph executions.
    for section in state["completed_sections"]:
        # Extract content based on the section type.
        if section["section_type"] == "main_signaling_pathway":
            main_pathway = section["content"]
        elif section["section_type"] == "expected_readouts":
            expected_readouts = section["content"]
    
    # Update the state with the initial, unrefined results.
    return {
        "main_pathway": main_pathway,
        "initial_readouts": expected_readouts
    }

def finalize_report(state: ExtendedReportState):
    """
    Creates the final, structured report for the user.

    This node takes the potentially refined readouts and combines them with
    the main pathway information into the final output format.
    """
    # Use the refined readouts if they exist; otherwise, fall back to the initial ones.
    final_readouts = state.get("refined_readouts")
    if not final_readouts:
        final_readouts = state.get("initial_readouts", "")
    
    # Instantiate the final Pydantic output model.
    final_report = PathwayAnalysisOutput(
        main_signaling_pathway=state.get("main_pathway", ""),
        expected_readouts=final_readouts
    )
    
    # Update the state with the completed report.
    return {"final_report": final_report}

def finalize_enhancement_report(state: FeedbackEnhancementState):
    enhanced_reactions = state["reactions"] + "\n" + "\n".join(state["added_reactions"])
    enhancement_summary = state["rationale"] + "\nSources:\n" + "- ".join([s + "\n" for s in state["sources"]])
    
    return {"original_reactions": state["reactions"],
            "enhanced_reactions": enhanced_reactions,
            "enhancement_summary": enhancement_summary}