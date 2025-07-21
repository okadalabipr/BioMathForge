from typing import Literal
from langgraph.types import Command
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END


from biomathforge.pathway_analyzer.utils.langchain_ai import (
    get_config_value,
    get_search_params,
    select_and_execute_search
)
from biomathforge.pathway_analyzer.configuration import Configuration
from biomathforge.pathway_analyzer.state import (
    SectionState, Queries, SectionContent,
    FeedbackEnhancementState, ReactionAdditions
)
from biomathforge.pathway_analyzer.prompts import (
    query_writer_instructions, section_writer_instructions,
    feedback_crosstalk_query_writer, reaction_enhancement_prompt
)


async def generate_queries(state: SectionState, config: RunnableConfig):
    """
    Generates targeted search queries for a specific analysis section using an LLM.
    """
    # Extract current state variables
    reactions = state["reactions"]
    experimental_condition = state.get("experimental_condition")
    section = state["section"]
    
    # Load configuration to determine the number of queries and LLM to use
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries
    
    # Initialize the chat model with structured output capabilities
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        **writer_model_kwargs
    )
    
    # Use different structured output methods based on the provider
    if writer_provider == "ollama":
        structured_llm = writer_model.with_structured_output(Queries, method="json_schema")
    else:
        structured_llm = writer_model.with_structured_output(Queries)
    
    # Dynamically add experimental condition to the prompt if it exists
    experimental_condition_section = ""
    experimental_condition_note = ""
    if experimental_condition:
        experimental_condition_section = f"<Experimental Condition>\n{experimental_condition}\n</Experimental Condition>\n"
        experimental_condition_note = "4. Consider the specific experimental condition when crafting queries"
    
    # Format the master prompt with all the necessary context
    system_instructions = query_writer_instructions.format(
        reactions=reactions,
        experimental_condition_section=experimental_condition_section,
        experimental_condition_note=experimental_condition_note,
        section_title=section.title,
        section_description=section.description,
        number_of_queries=number_of_queries
    )
    
    # Invoke the LLM to get a structured list of search queries
    queries = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries.")
    ])
    
    # Update the state with the generated queries
    return {"search_queries": queries.queries}

async def search_web(state: SectionState, config: RunnableConfig):
    """
    Executes web searches using the generated queries and a specified search API.
    """
    search_queries = state["search_queries"]
    
    # Load search API configuration
    configurable = Configuration.from_runnable_config(config)
    search_api = get_config_value(configurable.search_api)
    search_api_config = configurable.search_api_config or {}
    params_to_pass = get_search_params(search_api, search_api_config)
    
    # Extract search query strings from the structured objects
    query_list = [query.search_query for query in search_queries]
    
    # Execute the search and get a formatted string of results
    source_str = await select_and_execute_search(search_api, query_list, params_to_pass)
    
    # Update the state with the search results
    return {"source_str": source_str}

async def write_section(state: SectionState, config: RunnableConfig) -> Command[Literal[END]]:
    """
    Writes the final content for a section based on the web search results.
    """
    # Extract necessary variables from the state
    reactions = state["reactions"]
    experimental_condition = state.get("experimental_condition")
    section = state["section"]
    source_str = state["source_str"]
    
    # Load LLM configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    
    # Initialize the chat model with structured output for generating the section content
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        **writer_model_kwargs
    )
    
    if writer_provider == "ollama":
        structured_llm = writer_model.with_structured_output(SectionContent, method="json_schema")
    else:
        structured_llm = writer_model.with_structured_output(SectionContent)
    
    # Dynamically add experimental condition context to the prompt
    experimental_condition_section = ""
    experimental_condition_note = ""
    if experimental_condition:
        experimental_condition_section = f"<Experimental Condition>\n{experimental_condition}\n</Experimental Condition>\n"
        experimental_condition_note = "- Consider the specific experimental condition in your analysis"
    
    # Format the writing prompt with all context
    system_instructions = section_writer_instructions.format(
        reactions=reactions,
        experimental_condition_section=experimental_condition_section,
        experimental_condition_note=experimental_condition_note,
        section_title=section.title,
        section_description=section.description,
        context=source_str
    )
    
    # Invoke the LLM to generate the final, structured section content
    section_content = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Write the section content.")
    ])
    
    # Prepare the completed section data
    completed_section = {
        "section_type": section.section_type,
        "content": section_content.content,
        "sources": section_content.sources
    }
    
    # Return a command to update the main graph's state and end this subgraph's execution
    return Command(
        update={"completed_sections": [completed_section]},
        goto=END
    )

########################
### search nodes related to feedback loops and crosstalk analysis
########################

async def generate_feedback_queries(state: FeedbackEnhancementState, config: RunnableConfig):
    """
    Generates targeted search queries for feedback loops and crosstalk analysis using an LLM.
    """
    # Extract current state variables
    reactions = state["reactions"]
    source_nodes = state.get("source_nodes", "")
    sink_nodes = state.get("sink_nodes", "")
    main_signaling_pathways = state.get("main_signaling_pathways", "")
    expected_readouts = state.get("expected_readouts", "")
    
    # Load configuration to determine the number of queries and LLM to use
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries
    
    # Initialize the chat model with structured output capabilities
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        **writer_model_kwargs
    )
    
    # Use different structured output methods based on the provider
    if writer_provider == "ollama":
        structured_llm = writer_model.with_structured_output(Queries, method="json_schema")
    else:
        structured_llm = writer_model.with_structured_output(Queries)
    
    # Format the feedback/crosstalk query prompt with all the necessary context
    system_instructions = feedback_crosstalk_query_writer.format(
        reactions=reactions,
        source_nodes=source_nodes,
        sink_nodes=sink_nodes,
        main_signaling_pathways=main_signaling_pathways,
        expected_readouts=expected_readouts,
        number_of_queries=number_of_queries
    )
    
    # Invoke the LLM to get a structured list of search queries
    queries = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries for feedback loops and pathway crosstalk.")
    ])
    
    # Update the state with the generated queries
    return {"search_queries": queries.queries}

async def enhance_reactions(state: FeedbackEnhancementState, config: RunnableConfig) -> dict:
    """
    Enhances the reaction network by adding feedback loops and crosstalk reactions 
    based on web search results.
    """
    # Extract necessary variables from the state
    reactions = state["reactions"]
    source_str = state["source_str"]
    source_nodes = state["source_nodes"]
    sink_nodes = state["sink_nodes"]
    main_signaling_pathways = state.get("main_signaling_pathways", "")
    expected_readouts = state.get("expected_readouts", "")
    
    # Load LLM configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    
    # Initialize the chat model with structured output for generating reaction additions
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        **writer_model_kwargs
    )
    
    if writer_provider == "ollama":
        structured_llm = writer_model.with_structured_output(ReactionAdditions, method="json_schema")
    else:
        structured_llm = writer_model.with_structured_output(ReactionAdditions)
    
    # Format the enhancement prompt with all context
    system_instructions = reaction_enhancement_prompt.format(
        reactions=reactions,
        context=source_str,
        source_nodes=source_nodes,
        sink_nodes=sink_nodes,
        main_signaling_pathways=main_signaling_pathways,
        expected_readouts=expected_readouts
    )
    
    # Invoke the LLM to generate the additional reactions
    reaction_additions = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Identify and add feedback loops and crosstalk reactions.")
    ])
    
    # Return a dictionary to update the FeedbackEnhancementState
    return {
        "added_reactions": reaction_additions.added_reactions,
        "rationale": reaction_additions.rationale,
        "sources": reaction_additions.sources
    }