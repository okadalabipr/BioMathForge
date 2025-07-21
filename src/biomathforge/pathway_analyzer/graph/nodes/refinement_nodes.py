from typing import Literal
from langgraph.types import Command
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END

from biomathforge.pathway_analyzer.utils.langchain_ai import get_config_value
from biomathforge.pathway_analyzer.configuration import Configuration
from biomathforge.pathway_analyzer.state import ReadoutRefinementState, ReadoutRefinementDecision, ReadoutRefinementOutputState
from biomathforge.pathway_analyzer.prompts import readout_evaluation_instructions, readout_refinement_instructions


async def evaluate_readouts(state: ReadoutRefinementState, config: RunnableConfig) -> Command[Literal["prepare_output", "refine_readouts"]]:
    """
    Evaluates whether the current experimental readouts need refinement.

    This node acts as a router. It uses an LLM to decide if the readouts are
    sufficient or if they should be improved. It also includes a stop condition
    to prevent infinite loops.
    """
    # Extract current state variables
    reactions = state["reactions"]
    main_pathway = state["main_pathway"]
    current_readouts = state["current_readouts"]
    refinement_count = state["refinement_count"]
    
    # Stop condition: End the refinement loop after 3 iterations.
    if refinement_count >= 3:
        return Command(
            update={"final_readouts": current_readouts},
            goto="prepare_output" # Proceed to the final output mapping
        )
    
    # Load configuration for the LLM call
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    
    # Initialize the chat model with structured output capabilities
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        **writer_model_kwargs
    )
    
    # Use different structured output methods based on the provider
    if writer_provider == "ollama":
        structured_llm = writer_model.with_structured_output(ReadoutRefinementDecision, method="json_schema")
    else:
        structured_llm = writer_model.with_structured_output(ReadoutRefinementDecision)
    
    # Format the prompt with the current state information
    system_instructions = readout_evaluation_instructions.format(
        reactions=reactions,
        main_pathway=main_pathway,
        current_readouts=current_readouts
    )
    
    # Invoke the LLM to get a structured decision
    decision = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Evaluate the readouts.")
    ])
    
    # Route to the next node based on the LLM's decision
    if decision.should_refine:
        # If refinement is needed, update state with suggestions and go to the 'refine_readouts' node.
        return Command(
            update={"suggested_improvements": decision.suggested_improvements},
            goto="refine_readouts"
        )
    else:
        # If readouts are optimal, update the final readouts and go to the 'prepare_output' node.
        return Command(
            update={"final_readouts": current_readouts},
            goto="prepare_output"
        )


async def refine_readouts(state: ReadoutRefinementState, config: RunnableConfig):
    """
    Refines the current expected readouts based on suggestions from the evaluator.
    """
    # Extract current state variables
    reactions = state["reactions"]
    main_pathway = state["main_pathway"]
    current_readouts = state["current_readouts"]
    suggested_improvements = state.get("suggested_improvements", "")
    
    # Load LLM configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    
    # Initialize the chat model
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        **writer_model_kwargs
    )
    
    # Format the refinement prompt
    system_instructions = readout_refinement_instructions.format(
        reactions=reactions,
        main_pathway=main_pathway,
        current_readouts=current_readouts,
        suggested_improvements=suggested_improvements
    )
    
    # Invoke the LLM to get the refined text
    response = await writer_model.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Refine the readouts.")
    ])
    
    refined_readouts = response.content.strip()
    
    # Return the updated state for the next iteration of the loop
    return {
        "current_readouts": refined_readouts,
        "refinement_count": state["refinement_count"] + 1
    }

def map_refinement_output(state: ReadoutRefinementState) -> ReadoutRefinementOutputState:
    """
    Maps the final state of the refinement subgraph to its defined output schema.
    This is the last step before the subgraph returns its result.
    """
    # Use the 'final_readouts' if available, otherwise fall back to the last 'current_readouts'
    return {"refined_readouts": state.get("final_readouts", state.get("current_readouts", ""))}