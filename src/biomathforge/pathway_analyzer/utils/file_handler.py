import json
from typing import Tuple, Optional
from pydantic import BaseModel

from ...shared.utils.logger import BioMathForgeLogger

def load_enhancement_input(reactions_path: str,
                           terminal_nodes_path: str,
                           reactions_overviews_path: Optional[str] = None,
                           logger: Optional[BioMathForgeLogger] = None) -> Tuple[str, dict, dict]:
    """Load input files for pathway enhancement"""
    logger = logger or BioMathForgeLogger("enhancement_file_handler")

    try:
        # Reaction equations file (required)
        with open(reactions_path, 'r', encoding='utf-8') as f:
            reactions = f.read().strip()
        if not reactions:
            logger.error(f"❌ Reaction equations file is empty: {reactions_path}")
            return None, {}, {}
        logger.info(f"📄 Reaction equations file loaded: {reactions_path}")

        # Terminal nodes file (required)
        with open(terminal_nodes_path, 'r', encoding='utf-8') as f:
            terminal_nodes = json.load(f)
        if not terminal_nodes:
            logger.error(f"❌ Terminal nodes file is empty: {terminal_nodes_path}")
            return None, {}, {}
        logger.info(f"📄 Terminal nodes file loaded: {terminal_nodes_path}")

        # Reactions overviews file (optional)
        reactions_overviews = {"Main Signaling Pathway": "unknown",
                              "Expected Readouts": "unknown"}
        if reactions_overviews_path:
            with open(reactions_overviews_path, 'r', encoding='utf-8') as f:
                reactions_overviews_all = json.load(f)
            if not reactions_overviews_all:
                logger.warning(f"⚠️ Reactions overviews file is empty: {reactions_overviews_path}")
            else:
                logger.info(f"📄 Reactions overviews file loaded: {reactions_overviews_path}")
                reactions_overviews["Main Signaling Pathway"] = reactions_overviews_all.get("Main Signaling Pathway", "unknown")
                reactions_overviews["Expected Readouts"] = reactions_overviews_all.get("Expected Readouts", "unknown")
        else:
            logger.info("📄 No reactions overviews file specified")
        
        return reactions, terminal_nodes, reactions_overviews
    
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return None, {}, {}

def load_input_files(reactions_path: str, condition_path: Optional[str] = None,
                     logger: Optional[BioMathForgeLogger] = None) -> Tuple[str, Optional[str]]:
    """Load input files for pathway analysis"""
    logger = logger or BioMathForgeLogger("file_handler")
    try:
        # Reaction equations file (required)
        with open(reactions_path, 'r', encoding='utf-8') as f:
            reactions = f.read().strip()
        if not reactions:
            logger.error(f"❌ Reaction equations file is empty: {reactions_path}")
            return None, None
        logger.info(f"📄 Reaction equations file loaded: {reactions_path}")
        
        # Experimental condition file (optional)
        experimental_condition = None
        if condition_path:
            with open(condition_path, 'r', encoding='utf-8') as f:
                experimental_condition = f.read().strip()
            if not experimental_condition:
                logger.warning(f"⚠️ Experimental condition file is empty: {condition_path}")
            else:
                logger.info(f"📄 Experimental condition file loaded: {condition_path}")
        else:
            logger.info("📄 No experimental condition file specified")
        
        return reactions, experimental_condition
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return None, None

def save_analysis_results(report, reactions: str, experimental_condition: Optional[str], output_path: str,
                          logger: Optional[BioMathForgeLogger] = None) -> None:
    """save analysis results to a JSON file"""
    logger = logger or BioMathForgeLogger("file_handler")
    try:
        output_data = {
            "Reaction Equations": reactions,
            "Experimental Condition": experimental_condition,
            "Main Signaling Pathway": report.main_signaling_pathway,
            "Expected Readouts": report.expected_readouts
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        logger.info(f"✅ Analysis results saved: {output_path}")
        logger.info(f"\nMain Signaling Pathway: {report.main_signaling_pathway}\n"
                    f"\nExpected Readouts: {report.expected_readouts}")
        
    except Exception as e:
        logger.error(f"❌ Error saving results: {e}")

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)