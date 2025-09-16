from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from openai import OpenAI

from biomathforge.shared.ai.prompt_manager import PromptManager
from biomathforge.shared.ai.response_handler import ResponseHandler
from biomathforge.shared.utils.logger import BioMathForgeLogger


class ReactionFinalizer:
    """Reaction finalization class"""
    
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
        self.logger = logger or BioMathForgeLogger("reaction_finalizer")
        
        # AI client initialization
        # Note: Currently supports only the OpenAI API. Other LLM providers may be added in the future.
        # Assumes the environment variable OPENAI_API_KEY is set via dotenv.
        self.client = openai_client or OpenAI()
        self.config = config or {
            "planner_model": "o3-2025-04-16", 
            "writer_model": "o4-mini-2025-04-16", 
            "seed": 42
        }
        
        # Initialize the prompt manager
        self.prompt_manager = prompt_manager or PromptManager()
        
        # Initialize the response handler
        self.response_handler = ResponseHandler(
            openai_client=openai_client, 
            logger=logger, 
            prompt_manager=prompt_manager, 
            config=config
        )
    
    def prevent_divergence(
        self,
        equations: List[str]
    ) -> Optional[List[str]]:
        """
        Add missing decomposition reactions to prevent mass divergence
        
        Args:
            equations: List of reaction equations to process
            
        Returns:
            List of reaction equations with added decomposition reactions (None if failed)
        """
        self.logger.info(f"🔄 Starting mass divergence prevention process: {len(equations)} reaction equations")
        
        try:
            # Retrieve the system prompt and mass divergence prevention prompt
            system_prompt = self.prompt_manager.get_prompt("system_prompt")
            divergence_template = self.prompt_manager.get_prompt("prevent_divergence_prompt")
            
            if not system_prompt or not divergence_template:
                self.logger.error("❌ Divergence prevention prompt not found")
                return None
            
            # Create mass divergence prevention prompt
            divergence_prompt = divergence_template.format(
                reactions="\n".join(equations)
            ).strip()
            
            # AI API call
            completion = self.client.chat.completions.create(
                model=self.config["planner_model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": divergence_prompt}
                ],
                seed=self.config["seed"]
            )
            
            # Analyze the response
            content = completion.choices[0].message.content
            updated_equations = content.split("\n")
            updated_equations = [eq.strip() for eq in updated_equations if eq.strip()]
            
            self.logger.info(f"✅ Mass divergence prevention process completed: {len(updated_equations)} reaction equations")
            return updated_equations
            
        except Exception as e:
            self.logger.error(f"❌ Mass divergence prevention error: {e}")
            return None
    
    def finalize_activation_inhibition(
        self,
        equations: List[str]
    ) -> Optional[List[str]]:
        """
        Convert activation and inhibition reactions into Michaelis-Menten format
        
        Args:
            equations: List of reaction equations to process
            
        Returns:
            List of finalized reaction equations (None if failed)
        """
        self.logger.info(f"🔄 Starting the finalization of activation and inhibition reactions: {len(equations)} reaction equations")
        
        try:
            # Retrieve the activation and inhibition rewrite prompt
            activation_template = self.prompt_manager.get_prompt("rewrite_activation_inhibition_prompt")
            
            if not activation_template:
                self.logger.error("❌ Could not find a prompt for activation/inhibition rewriting.")
                return None
            
            # Create rewrite prompt
            rewrite_prompt = activation_template.format(
                reactions="\n".join(equations)
            ).strip()
            
            # AI API call (without system prompt)
            completion = self.client.chat.completions.create(
                model=self.config["planner_model"],
                messages=[
                    {"role": "user", "content": rewrite_prompt}
                ],
                seed=self.config["seed"]
            )
            
            # Analyze the response
            content = completion.choices[0].message.content
            finalized_equations = content.split("\n")
            finalized_equations = [eq.strip() for eq in finalized_equations if eq.strip()]
            
            self.logger.info(f"✅ Finalization of activation and inhibition reactions completed: {len(finalized_equations)} reaction equations")
            return finalized_equations
            
        except Exception as e:
            self.logger.error(f"❌ Finalization of activation and inhibition reactions error: {e}")
            return None


def finalize_reactions(
    equations: List[str],
    openai_client: Optional[OpenAI] = None,
    prompt_manager: Optional[PromptManager] = None,
    config: Optional[Dict[str, Any]] = None,
    prevent_divergence: bool = True,
    finalize_activation: bool = True,
    validate_format: bool = True,
    max_iterations: int = 3,
    save_intermediate: bool = False,
    output_dir: Optional[Path] = None,
    logger: Optional[BioMathForgeLogger] = None
) -> Optional[List[str]]:
    """
    Finalize reaction equations and convert them into a simulation-compatible format
    
    Args:
        equations: List of reaction equations to finalize
        openai_client: OpenAI client
        prompt_manager: Instance of the prompt manager
        config: Configuration dictionary
        prevent_divergence: Whether to perform mass divergence prevention
        finalize_activation: Whether to finalize activation and inhibition reactions
        validate_format: Whether to validate the format of the equations
        max_iterations: Maximum number of attempts for format validation
        save_intermediate: Whether to save intermediate results
        output_dir: Directory to save intermediate results
        logger: Logger instance
        
    Returns:
        List of finalized reaction equations (None if failed)
    """
    logger = logger or BioMathForgeLogger("finalize_reactions")
    
    try:
        logger.info(f"🎯 Starting reaction finalization: {len(equations)} reaction equations")
        
        # Initialize the finalizer
        finalizer = ReactionFinalizer(
            openai_client=openai_client,
            prompt_manager=prompt_manager,
            config=config,
            logger=logger
        )
        
        current_equations = equations.copy()
        
        # Phase 1: Divergence Prevention Process
        if prevent_divergence:
            logger.info("🔄 Phase 1: Divergence Prevention Process (Adding Decomposition Reactions)")
            
            updated_equations = finalizer.prevent_divergence(current_equations)
            
            if updated_equations is not None:
                current_equations = updated_equations
                logger.info(f"✅ Divergence prevention process completed: {len(current_equations)} reactions")
                
                # Format validation
                if validate_format:
                    validated = finalizer.response_handler.validate_equations_format(
                        current_equations, 
                        max_iterations=max_iterations
                    )
                    if validated is not None:
                        current_equations = validated
                        logger.info(f"✅ Format validation after divergence prevention completed: {len(current_equations)} reactions")
                
                # Save intermediate results
                if save_intermediate and output_dir:
                    output_dir = Path(output_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    with open(output_dir / "finalized_equations_divergence_prevented.txt", 'w', encoding='utf-8') as f:
                        for eq in current_equations:
                            f.write(eq + "\n")
                    logger.info(f"💾 Saved divergence prevention results: {len(current_equations)} reactions")
                
                logger.info("\n" + "\n".join(current_equations))
                    
            else:
                logger.warning("⚠️ Mass divergence prevention process failed, but continuing with the process")
        
        # Phase 2: Finalization of activation and inhibition reactions
        if finalize_activation:
            logger.info("🔄 Phase 2: Finalization of activation and inhibition reactions")
            
            finalized_equations = finalizer.finalize_activation_inhibition(current_equations)
            
            if finalized_equations is not None:
                current_equations = finalized_equations
                logger.info(f"✅ Finalization of activation and inhibition reactions completed: {len(current_equations)} reactions")
                
                # Save final results
                if save_intermediate and output_dir:
                    with open(output_dir / "finalized_equations_complete.txt", 'w', encoding='utf-8') as f:
                        for eq in current_equations:
                            f.write(eq + "\n")
                    logger.info(f"💾 Saved final results: {len(current_equations)} reactions")
                    
                logger.info("\n" + "\n".join(current_equations))
            else:
                logger.warning("⚠️ Finalization of activation and inhibition reactions failed, but returning the existing results")
        
        logger.info(f"🎉 Reaction finalization completed! Final result: {len(current_equations)} reaction equations")
        return current_equations
        
    except Exception as e:
        logger.error(f"❌ An error occurred during reaction finalization: {e}")
        return None


def finalize_reactions_from_file(
    equations_file: Union[str, Path],
    **kwargs
) -> Optional[List[str]]:
    """
    Load reaction equations from a file and finalize them
    
    Args:
        equations_file: Path to the file containing reaction equations (one equation per line)
        **kwargs: Additional arguments for finalize_reactions
        
    Returns:
        List of finalized reaction equations (None if failed)
    """
    logger = kwargs.get('logger', BioMathForgeLogger("finalize_from_file"))
    
    try:
        # Load reaction equations file
        with open(equations_file, 'r', encoding='utf-8') as f:
            equations_content = f.read()
        equations = [eq.strip() for eq in equations_content.split('\n') if eq.strip()]
        
        logger.info(f"📂 File loading completed:")
        logger.info(f"  Reactions: {len(equations)} items")
        logger.info(f"  File: {equations_file}")
        
        # Execute finalization
        return finalize_reactions(
            equations=equations,
            **kwargs
        )
        
    except Exception as e:
        logger.error(f"❌ File loading error: {e}")
        return None
