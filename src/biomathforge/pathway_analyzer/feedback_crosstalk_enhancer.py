from typing import Optional, List, Dict, Any, Tuple
import uuid
import json
from langgraph.checkpoint.memory import MemorySaver

from biomathforge.shared.utils.logger import BioMathForgeLogger
from biomathforge.pathway_analyzer.utils.file_handler import load_enhancement_input, CustomEncoder
from biomathforge.pathway_analyzer.configuration import Configuration
from biomathforge.pathway_analyzer.graph.builder import build_feedback_crosstalk_graph

async def run_enhance_feedback_crosstalk(
    reactions_path: str,
    terminal_nodes_path: str,
    reactions_overviews_path: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[BioMathForgeLogger] = None
) -> Tuple[Optional[str], str, List[str]]:
    """
    Execute pathway enhancement with feedback and crosstalk analysis
    
    Args:
        reactions_path: Path to reactions file
        terminal_nodes_path: Path to terminal nodes file
        reactions_overviews_path: Path to reactions overviews file
        config: Analysis configuration
        logger: Logger instance
        
    Returns:
        final_report: The final report of the pathway enhancement or None if an error occurred
        enhancement_summary: Summary of the enhancement process
        added_reactions: List of added reactions during the enhancement
    """
    logger = logger or BioMathForgeLogger("pathway_enhancement")
    
    try:
        # 1. Load input files
        reactions, terminal_nodes_dict, reactions_overviews = load_enhancement_input(reactions_path, terminal_nodes_path, reactions_overviews_path)
        if reactions is None:
            return None, {}, []
        # 1-1. Parse dict
        source_nodes = terminal_nodes_dict["source"]
        sink_nodes = terminal_nodes_dict["sink"]
        main_signaling_pathways = reactions_overviews["Main Signaling Pathway"]
        expected_readouts = reactions_overviews["Expected Readouts"]
        
        # 2. Build the main graph
        memory = MemorySaver()
        graph = build_feedback_crosstalk_graph(memory)
        
        # 3. Configure the analysis thread
        default_config = Configuration().to_dict()
        default_config["number_of_queries"] = 6
        if config is None:
            config = default_config
        else:
            default_config.update(config)
            config = default_config
        thread = {"configurable": {"thread_id": str(uuid.uuid4()),
                                    "search_api": config["search_api"],
                                    "planner_provider": config["planner_provider"],
                                    "planner_model": config["planner_model"],
                                    "planner_model_kwargs": {"seed": config["seed"]},
                                    "writer_provider": config["writer_provider"],
                                    "writer_model": config["writer_model"],
                                    "writer_model_kwargs": {"seed": config["seed"]},
                                    "number_of_queries": config["number_of_queries"],
                                    "max_search_depth": config["max_search_depth"],
                                    }}
        
        # 4. Start the analysis
        logger.info("🚀 Starting pathway enhancement")
        
        final_state = None
        async for event in graph.astream(
            {"reactions": reactions, "source_nodes": source_nodes, "sink_nodes": sink_nodes, "main_signaling_pathways": main_signaling_pathways, "expected_readouts": expected_readouts},
            thread,
            stream_mode="updates"
        ):
            if "search_web" in event:
                # Truncate the output because it can be very long
                event["search_web"]["source_str"] = event["search_web"]["source_str"][:200] + "..." if len(event["search_web"]["source_str"]) > 200 else event["search_web"]["source_str"]
            logger.info(f"📊 Event: \n{json.dumps(event, indent=4, cls=CustomEncoder, ensure_ascii=False)}")
        
        # 5. Get the final state
        final_state = graph.get_state(thread)
        final_report = final_state.values.get('enhanced_reactions')
        enhancement_summary = final_state.values.get('enhancement_summary', "")
        added_reactions = final_state.values.get('added_reactions', [])
        
        if final_report:
            logger.info("✅ Pathway enhancement completed")
            return final_report, enhancement_summary, added_reactions
        else:
            logger.error("❌ Final report was not generated")
            return None, "", []
            
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return None, "", []