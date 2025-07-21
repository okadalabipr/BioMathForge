from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph

from biomathforge.pathway_analyzer.configuration import Configuration
from biomathforge.pathway_analyzer.state import (ReportState, SectionState, SectionOutputState, ReadoutRefinementState, ReadoutRefinementOutputState,
                     ExtendedReportState, ReportStateInput, ReportStateOutput,
                     FeedbackEnhancementState, FeedbackEnhancementInput, FeedbackEnhancementOutput)
from biomathforge.pathway_analyzer.graph.nodes.analysis_nodes import (generate_sections, gather_completed_sections, finalize_report,
                                   finalize_enhancement_report)
from biomathforge.pathway_analyzer.graph.nodes.search_nodes import (generate_queries, search_web, write_section,
                                 generate_feedback_queries, enhance_reactions)
from biomathforge.pathway_analyzer.graph.nodes.refinement_nodes import evaluate_readouts, refine_readouts, map_refinement_output


def kick_off_section_building(state: ReportState):
    """
    Router function for a conditional edge.
    It takes the generated sections and dispatches a parallel task for each one
    to the `build_section_with_web_research` subgraph node.
    """
    return [
        Send("build_section_with_web_research", {
            "reactions": state["reactions"],
            "experimental_condition": state.get("experimental_condition"),
            "section": section,
        })
        for section in state["sections"]
    ]

def kick_off_readout_refinement(state: ReportState):
    """
    Router function for a conditional edge.
    It dispatches a task to the `refine_readouts_subgraph` to start the
    iterative refinement process.
    """
    return Send("refine_readouts_subgraph", {
        "reactions": state["reactions"],
        "main_pathway": state.get("main_pathway", ""),
        "current_readouts": state.get("initial_readouts", ""),
        "refinement_count": 0
    })

def build_main_graph(memory):
    """
    Constructs and compiles the complete, multi-level LangGraph for pathway analysis.

    This function defines two subgraphs (for section building and readout refinement)
    and integrates them into a main graph that controls the overall workflow.

    Args:
        memory: A checkpointer instance (e.g., MemorySaver) for saving graph state.

    Returns:
        A compiled, runnable graph object.
    """

    # --- 1. Define the Section Builder Subgraph ---
    # This subgraph performs a linear sequence: generate queries -> search -> write content.
    section_builder = StateGraph(SectionState, output=SectionOutputState)
    section_builder.add_node("generate_queries", generate_queries)
    section_builder.add_node("search_web", search_web)
    section_builder.add_node("write_section", write_section)
    
    # Define the linear flow of the subgraph
    section_builder.add_edge(START, "generate_queries")
    section_builder.add_edge("generate_queries", "search_web")
    section_builder.add_edge("search_web", "write_section")
    # The `write_section` node returns a Command to END the subgraph, so no edge to END is needed here.

    # --- 2. Define the Readout Refinement Subgraph ---
    # This subgraph iteratively evaluates and refines the expected readouts.
    refinement_builder = StateGraph(ReadoutRefinementState, output=ReadoutRefinementOutputState)
    refinement_builder.add_node("evaluate_readouts", evaluate_readouts)
    refinement_builder.add_node("refine_readouts", refine_readouts)
    refinement_builder.add_node("prepare_output", map_refinement_output)
    
    # Define the flow, including the refinement loop
    refinement_builder.add_edge(START, "evaluate_readouts")
    refinement_builder.add_edge("refine_readouts", "evaluate_readouts") # The loop back to evaluation
    refinement_builder.add_edge("prepare_output", END) # The final output mapping step
    
    # The `evaluate_readouts` node uses a Command to decide whether to go to 
    # `refine_readouts` or `prepare_output`, so no conditional edge is needed here.
    refinement_graph = refinement_builder.compile()


    # --- 3. Define the Main Graph ---
    # This is the primary graph that orchestrates the subgraphs and the overall process.
    builder = StateGraph(ExtendedReportState, input=ReportStateInput, output=ReportStateOutput, config_schema=Configuration)

    # Add all nodes to the main graph
    builder.add_node("generate_sections", generate_sections)
    builder.add_node("build_section_with_web_research", section_builder.compile())
    builder.add_node("gather_completed_sections", gather_completed_sections)
    builder.add_node("refine_readouts_subgraph", refinement_graph)
    builder.add_node("finalize_report", finalize_report)

    # Wire the nodes together to define the application's flow
    builder.add_edge(START, "generate_sections")
    builder.add_conditional_edges(
        "generate_sections",
        kick_off_section_building,
        ["build_section_with_web_research"] # This name must match the `Send` target
    )
    builder.add_edge("build_section_with_web_research", "gather_completed_sections")
    builder.add_conditional_edges(
        "gather_completed_sections",
        kick_off_readout_refinement,
        ["refine_readouts_subgraph"] # This name must match the `Send` target
    )
    builder.add_edge("refine_readouts_subgraph", "finalize_report")
    builder.add_edge("finalize_report", END)
    
    # --- 4. Compile the Final Graph ---
    # This creates the final, executable graph object, linking it to the checkpointer.
    graph = builder.compile(checkpointer=memory)
    
    return graph

def build_feedback_crosstalk_graph(memory):
    builder = StateGraph(FeedbackEnhancementState, input=FeedbackEnhancementInput, output=FeedbackEnhancementOutput, config_schema=Configuration)

    # Add all nodes and edges to the main graph
    builder.add_node("generate_queries", generate_feedback_queries)
    builder.add_node("search_web", search_web)
    builder.add_node("write_section", enhance_reactions)
    builder.add_node("finalize_report", finalize_enhancement_report)

    builder.add_edge(START, "generate_queries")
    builder.add_edge("generate_queries", "search_web")
    builder.add_edge("search_web", "write_section")
    builder.add_edge("write_section", "finalize_report")
    builder.add_edge("finalize_report", END)

    # Compile the final graph
    graph = builder.compile(checkpointer=memory)
    return graph