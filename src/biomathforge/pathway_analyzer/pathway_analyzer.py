from typing import Optional, List, Dict, Any
import uuid
import json
from langgraph.checkpoint.memory import MemorySaver

from biomathforge.shared.utils.logger import BioMathForgeLogger
from biomathforge.pathway_analyzer.utils.file_handler import load_input_files, CustomEncoder
from biomathforge.pathway_analyzer.configuration import Configuration
from biomathforge.pathway_analyzer.graph.builder import build_main_graph

async def run_pathway_analysis(
    reactions_path: str,
    condition_path: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[BioMathForgeLogger] = None
) -> Optional[Dict[str, Any]]:
    """
    Execute pathway analysis
    
    Args:
        reactions_path: Path to reactions file
        condition_path: Path to experimental conditions file
        config: Analysis configuration
        logger: Logger instance
        
    Returns:
        final_report: The final report of the pathway analysis or None if an error occurred
    """
    logger = logger or BioMathForgeLogger("pathway_analysis")
    
    try:
        # 1. Load input files
        reactions, experimental_condition = load_input_files(reactions_path, condition_path)
        if reactions is None:
            return None
        
        # 2. Build the main graph
        memory = MemorySaver()
        graph = build_main_graph(memory)
        
        # 3. Configure the analysis thread
        default_config = Configuration().to_dict()
        default_config["number_of_queries"] = 4
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
        logger.info("🚀 Starting pathway analysis")
        
        final_state = None
        async for event in graph.astream(
            {"reactions": reactions, "experimental_condition": experimental_condition},
            thread,
            stream_mode="updates"
        ):
            logger.info(f"📊 Event: \n{json.dumps(event, indent=4, cls=CustomEncoder, ensure_ascii=False)}")
        
        # 5. Get the final state
        final_state = graph.get_state(thread)
        final_report = final_state.values.get('final_report')
        
        if final_report:
            logger.info("✅ Pathway analysis completed")
            return final_report
        else:
            logger.error("❌ Final report was not generated")
            return None
            
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return None