import json
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from openai import OpenAI

from biomathforge.shared.ai.prompt_manager import PromptManager
from biomathforge.shared.ai.response_handler import ResponseHandler
from biomathforge.shared.utils.logger import BioMathForgeLogger
from biomathforge.network_builder.validation.continuity_checker import find_terminal_nodes
from biomathforge.network_builder.validation.network_analyzer import parse_lines_to_dataframe


class ReactionIntegrator:
    """Reaction Integration Class"""
    
    def __init__(
        self, 
        openai_client: Optional[OpenAI] = None,
        prompt_manager: Optional[PromptManager] = None,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[BioMathForgeLogger] = None
    ):
        """
        Initialization
        
        Args:
            openai_client: OpenAI client (automatically created from environment variables if not specified)
            prompt_manager: Instance of the prompt manager
            config: Configuration dictionary
            logger: Logger instance
        """
        self.logger = logger or BioMathForgeLogger("reaction_integrator")
        
        # AI client initialization
        # Note: Currently supports only the OpenAI API. Other LLM providers may be added in the future.
        # Assumes the environment variable OPENAI_API_KEY is set via dotenv.
        self.client = openai_client or OpenAI()
        self.config = config or {
            "planner_model": "o3-2025-04-16", 
            "writer_model": "o4-mini-2025-04-16", 
            "seed": 42
        }
        
        # Initialize prompt manager
        self.prompt_manager = prompt_manager or PromptManager()
        
        # Initialize the response handler
        self.response_handler = ResponseHandler(
            openai_client=openai_client, 
            logger=logger, 
            prompt_manager=prompt_manager, 
            config=config
        )
    
    def integrate_equations(
        self,
        equations: List[str],
        main_signaling_pathways: str,
        expected_readouts: str
    ) -> Optional[List[str]]:
        """
        Integrate reactions to construct a network
        
        Args:
            equations: List of reactions to integrate
            main_signaling_pathways: Main signaling pathways
            expected_readouts: Expected readouts
            
        Returns:
            List of integrated reactions (None if failed)
        """
        self.logger.info(f"🔗 Integrating {len(equations)} reactions...")
        
        try:
            # システムプロンプトと統合プロンプトを取得
            system_prompt = self.prompt_manager.get_prompt("system_prompt")
            integration_template = self.prompt_manager.get_prompt("integrate_model_prompt")
            
            if not system_prompt or not integration_template:
                self.logger.error("❌ Integration prompts not found")
                return None
            
            # 統合プロンプト作成
            integration_prompt = integration_template.format(
                equations="\n".join(equations),
                main_signaling_pathways=main_signaling_pathways,
                expected_readouts=expected_readouts
            ).strip()
            
            # AI API 呼び出し
            completion = self.client.chat.completions.create(
                model=self.config["planner_model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": integration_prompt}
                ],
                seed=self.config["seed"]
            )
            
            # 応答の解析
            content = completion.choices[0].message.content
            integrated_equations = content.split("\n")
            integrated_equations = [eq.strip() for eq in integrated_equations if eq.strip()]    
            
            self.logger.info(f"✅ Generated {len(integrated_equations)} integrated reactions")
            return integrated_equations
            
        except Exception as e:
            self.logger.error(f"❌ Reaction integration error: {e}")
            return None
    
    def drop_duplicates(
        self,
        equations: List[str]
    ) -> Optional[List[str]]:
        """
        Remove duplicate reactions
        
        Args:
            equations: List of reaction equations to process
            
        Returns:
            List of deduplicated reaction equations (None if failed)
        """
        self.logger.info(f"🔄 Removing duplicate reactions")
        
        try:
            # Retrieve system prompt and duplicate removal prompt
            system_prompt = self.prompt_manager.get_prompt("system_prompt")
            duplicate_template = self.prompt_manager.get_prompt("drop_duplicate_prompt")
            
            if not system_prompt or not duplicate_template:
                self.logger.error(f"❌ Duplicate removal prompt not found")
                return None
            
            # Create duplicate removal prompt
            dedup_prompt = duplicate_template.format(
                raw_reactions="\n".join(equations)
            ).strip()
            
            # AI API call
            completion = self.client.chat.completions.create(
                model=self.config["planner_model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": dedup_prompt}
                ],
                seed=self.config["seed"]
            )
            
            # Parse the response
            content = completion.choices[0].message.content
            deduplicated_equations = content.split("\n")
            deduplicated_equations = [eq.strip() for eq in deduplicated_equations if eq.strip()]
            
            self.logger.info(f"✅ {len(deduplicated_equations)} reactions remain after duplicate removal")
            return deduplicated_equations
            
        except Exception as e:
            self.logger.error(f"❌ Duplicate removal error: {e}")
            return None


def integrate_reactions(
    equations: List[str],
    reactions_overviews: Dict[str, Any] = {},
    openai_client: Optional[OpenAI] = None,
    prompt_manager: Optional[PromptManager] = None,
    config: Optional[Dict[str, Any]] = None,
    validate_format: bool = True,
    check_connectivity: bool = True,
    max_iterations: int = 3,
    max_connectivity_iterations: int = 10,
    save_intermediate: bool = False,
    output_dir: Optional[Path] = None,
    logger: Optional[BioMathForgeLogger] = None
) -> Optional[List[str]]:
    """
    Integrate reaction equations to construct a continuous network
    
    Args:
        equations: List of reaction equations to integrate
        reactions_overviews: Dictionary of reaction overviews (contents of pathway_analysis_result.json)
        openai_client: OpenAI client
        prompt_manager: Instance of the prompt manager
        config: Configuration dictionary
        validate_format: Whether to validate the format
        check_connectivity: Whether to check network connectivity
        max_iterations: Maximum number of attempts for format validation
        max_connectivity_iterations: Maximum number of attempts to ensure connectivity
        save_intermediate: Whether to save intermediate results
        output_dir: Directory to save intermediate results
        logger: Logger instance
        
    Returns:
        List of integrated and validated reaction equations (None if failed)
    """
    logger = logger or BioMathForgeLogger("integrate_reactions")
    
    try:
        # Extract key information from reaction overviews
        main_signaling_pathways = reactions_overviews.get("Main Signaling Pathway", "").strip()
        expected_readouts = reactions_overviews.get("Expected Readouts", "").strip()
        
        if not main_signaling_pathways or not expected_readouts:
            main_signaling_pathways = "Unknown"
            expected_readouts = "Unknown"
            logger.warning("⚠️ Main signaling pathways or expected readouts are not specified. Using default values.")
            return None, None, None
        
        logger.info(f"🔗 Starting reaction integration: {len(equations)} reactions")
        logger.info(f"📊 Main pathways: {main_signaling_pathways[:50]}...")
        logger.info(f"📊 Expected readouts: {expected_readouts[:50]}...")
        
        # Initialize the integrator
        integrator = ReactionIntegrator(
            openai_client=openai_client,
            prompt_manager=prompt_manager,
            config=config,
            logger=logger
        )
        
        # Phase 1: Basic Integration
        logger.info("🔄 Phase 1: Basic integration of reaction equations")
        integrated_equations = integrator.integrate_equations(
            equations=equations,
            main_signaling_pathways=main_signaling_pathways,
            expected_readouts=expected_readouts
        )
        
        if integrated_equations is None:
            logger.error("❌ Failed basic integration")
            return None, None, None
        
        # Phase 2: Format Validation
        if validate_format:
            logger.info("🔍 Phase 2: Format validation")
            validated_equations = integrator.response_handler.validate_equations_format(
                integrated_equations, 
                max_iterations=max_iterations
            )
            
            if validated_equations is None:
                logger.warning("⚠️ Format validation failed, but the integrated results will be used as is.")
                validated_equations = integrated_equations
            else:
                # Save intermediate results
                if save_intermediate and output_dir:
                    output_dir = Path(output_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    with open(output_dir / "integrated_equations_first_round.txt", 'w', encoding='utf-8') as f:
                        for eq in integrated_equations:
                            f.write(eq + "\n")
                    logger.info(f"💾 Saved first-stage integration results: {len(integrated_equations)} reactions")
                
                integrated_equations = validated_equations
                logger.info(f"✅ Format validation completed: {len(integrated_equations)} reactions")
                logger.info("\n" + "\n".join(integrated_equations))
        
        # Phase 3: Removing duplicate reactions
        logger.info("🔄 Phase 3: Removing duplicate reactions")
        
        # 3-1: Basic duplicate removal
        deduplicated_equations = integrator.drop_duplicates(
            integrated_equations
        )
        
        if deduplicated_equations is not None:
            integrated_equations = deduplicated_equations
            
            # Format validation
            if validate_format:
                validated = integrator.response_handler.validate_equations_format(
                    integrated_equations, 
                    max_iterations=max_iterations
                )
                if validated is not None:
                    integrated_equations = validated
            
            # Save intermediate results
            if save_intermediate and output_dir:
                with open(output_dir / "integrated_equations_dropped_duplicates.txt", 'w', encoding='utf-8') as f:
                    for eq in integrated_equations:
                        f.write(eq + "\n")
                logger.info(f"💾 Saved results after duplicate removal: {len(integrated_equations)} reactions")
            
            logger.info("\n" + "\n".join(integrated_equations))
        else:
            logger.warning("⚠️ Duplicate removal failed, but the integrated results will be used as is")
        
        
        # Phase 4: Ensuring network connectivity
        if check_connectivity:
            logger.info("🔗 Phase 4: Ensuring network connectivity")
            
            # Use validate_equations_connectivity from ResponseHandler
            final_equations = integrator.response_handler.validate_equations_connectivity(
                equations=integrated_equations,
                logger=logger,
                expected_readouts=expected_readouts,
                main_signaling_pathways=main_signaling_pathways,
                max_iter=max_connectivity_iterations
            )
            
            if final_equations is not None:
                integrated_equations = final_equations
                logger.info(f"✅ Ensured network connectivity: {len(integrated_equations)} reactions")
            else:
                logger.warning("⚠️ Failed to ensure network connectivity, returning existing results")
        
        # Save final results
        if save_intermediate and output_dir:
            with open(output_dir / "integrated_equations_final.txt", 'w', encoding='utf-8') as f:
                for eq in integrated_equations:
                    f.write(eq + "\n")
            logger.info(f"💾 Saved final integration results: {len(integrated_equations)} reactions")
        
        logger.info("\n" + "\n".join(integrated_equations))
        
        logger.info(f"🎉 Reaction integration completed! Final result: {len(integrated_equations)} reactions")

        # Analyze the network to get the source and sink reactions
        network_df = parse_lines_to_dataframe(integrated_equations)
        source_nodes, sink_nodes = find_terminal_nodes(network_df, logger=logger)

        return integrated_equations, source_nodes, sink_nodes
        
    except Exception as e:
        logger.error(f"❌ An error occurred during reaction integration: {e}")
        return None, None, None


def integrate_reactions_from_files(
    equations_file: Union[str, Path],
    reactions_overviews_file: Union[str, Path] = None,
    **kwargs
) -> Optional[List[str]]:
    """
    Load reaction equations and overviews from files and integrate them
    
    Args:
        equations_file: Path to the file containing reaction equations (one equation per line)
        reactions_overviews_file: Path to the JSON file containing reaction overviews
        **kwargs: Additional arguments to pass to integrate_reactions
        
    Returns:
        List of integrated reaction equations (None if failed)
    """
    logger = kwargs.get('logger', BioMathForgeLogger("integrate_from_files"))
    
    try:
        # Load reaction equations file
        with open(equations_file, 'r', encoding='utf-8') as f:
            equations_content = f.read()
        equations = [eq.strip() for eq in equations_content.split('\n') if eq.strip()]
        
        # Load reaction overview JSON
        if reactions_overviews_file is None:
            reactions_overviews = {}
        else:
            with open(reactions_overviews_file, 'r', encoding='utf-8') as f:
                reactions_overviews = json.load(f)
        
        logger.info(f"📂 File loading completed:")
        logger.info(f"  Reactions: {len(equations)} items")
        logger.info(f"  Pathway analysis file: {reactions_overviews_file}")

        # Start integration
        return integrate_reactions(
            equations=equations,
            reactions_overviews=reactions_overviews,
            **kwargs
        )
        
    except Exception as e:
        logger.error(f"❌ File loading error: {e}")
        return None
