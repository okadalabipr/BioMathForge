import re
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
from openai import OpenAI

from biomathforge.shared.utils.logger import BioMathForgeLogger
from biomathforge.shared.ai.prompt_manager import PromptManager
from biomathforge.network_builder.validation.format_checker import BioModelFormatValidator
from biomathforge.network_builder.validation.network_analyzer import parse_lines_to_dataframe
from biomathforge.network_builder.validation.continuity_checker import check_network_continuity


class ResponseHandler:
    """AI response analysis, validation, and format processing"""
    
    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        logger: Optional[BioMathForgeLogger] = None,
        prompt_manager: Optional[PromptManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.client = openai_client or OpenAI()
        self.logger = logger or BioMathForgeLogger("response_handler")
        self.validator = BioModelFormatValidator(logger=self.logger)
        self.prompt_manager = prompt_manager or PromptManager()
        self.config = config or {"planner_model": "o3-2025-04-16", "writer_model": "o4-mini-2025-04-16", "seed": 42}
    
    def _log_invalid_lines(self, invalid_lines: List[str]) -> None:
        """Log invalid lines"""
        self.logger.warning("Invalid lines:")
        self.logger.warning("-" * 50)
        for line in invalid_lines:
            self.logger.warning(f"  ❌ {line}")
        self.logger.warning("-" * 50)
    
    def _attempt_correction(
        self,
        invalid_lines: List[str],
        system_prompt: str,
        rewrite_template: str
    ) -> Optional[List[str]]:
        """
        Attempt to correct invalid lines using LLM
        (Currently assumes OpenAI API only)

        Args:
            invalid_lines: Invalid lines to be corrected
            system_prompt: System prompt
            rewrite_template: Prompt template for correction

        Returns:
            Optional[List[str]]: Corrected reaction equations (None if failed)
        """
        try:
            self.logger.info("🤖 Attempting automatic correction with AI...")

            # 修正プロンプトの構築
            invalid_text = "\n".join(invalid_lines)
            correction_prompt = rewrite_template.format(invalid_lines=invalid_text).strip()

            # AI API 呼び出し
            completion = self.client.chat.completions.create(
                model=self.config["writer_model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": correction_prompt}
                ],
                seed= self.config["seed"],
            )

            corrected_response = completion.choices[0].message.content
            corrected_lines = [
                line.strip()
                for line in corrected_response.strip().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

            self.logger.info(f"✅ Obtained {len(corrected_lines)} corrected reaction equations")
            return corrected_lines

        except Exception as e:
            self.logger.error(f"Error occurred during AI correction: {e}")
            return None
    

    def validate_equations_format(
        self, 
        equations: Union[List[str], np.ndarray], 
        max_iterations: int = 3
    ) -> Optional[List[str]]:
        """
        Validate reaction equation format and perform automatic correction
        Uses PromptManager to retrieve prompts
        """
        if isinstance(equations, np.ndarray):
            equations = equations.tolist()
        
        valid_lines = []
        current_equations = [eq.strip() for eq in equations if isinstance(eq, str) and eq.strip()]
        
        self.logger.info(f"🔍 Starting validation of {len(equations)} reaction equations")
        
        for iteration in range(max_iterations):
            self.logger.info(f"🔄 Validation round {iteration + 1}/{max_iterations}")
            text_to_validate = "\n".join(current_equations)
            is_valid, invalid_lines = self.validator.check_format(text_to_validate)
            
            if is_valid:
                self.logger.info("✅ All reaction equations have valid format")
                valid_lines.extend(current_equations)
                return valid_lines

            self.logger.warning(f"⚠️ Detected {len(invalid_lines)} lines with invalid format")
            self._log_invalid_lines(invalid_lines)
            valid_lines.extend([eq for eq in current_equations if eq not in invalid_lines])

            # プロンプト取得
            try:
                system_prompt = self.prompt_manager.get_prompt("system_prompt")
                rewrite_template = self.prompt_manager.get_prompt("rewrite_prompt")
            except KeyError as e:
                self.logger.error(f"Prompt not found: {e}")
                break
            
            # 無効行の修正
            current_equations = self._attempt_correction(
                invalid_lines, system_prompt, rewrite_template
            )
            if not current_equations:
                break

        # 最終チェックとログ
        self.logger.warning(f"⚠️ Maximum number of attempts ({max_iterations}) reached")
        final_text = "\n".join(current_equations)
        _, final_invalid_lines = self.validator.check_format(final_text)
        if final_invalid_lines:
            self.logger.error("❌ The following lines could not be corrected:")
            self._log_invalid_lines(final_invalid_lines)
            final_valid = [eq for eq in current_equations if eq not in final_invalid_lines]
            valid_lines.extend(final_valid)

        return valid_lines if valid_lines else None
    
    def describe_subnetworks(
        self,
        sources: List[List[str]],
        sinks: List[List[str]]
    ) -> str:
        """
        Describe subnetworks from lists of sources and sinks.

        Args:
            sources: List of source node lists per subnetwork
            sinks: List of sink node lists per subnetwork

        Returns:
            Description string for subnetworks
        """
        descs = []
        for i, (subG_sources, subG_sinks) in enumerate(zip(sources, sinks)):
            descs.append(f"### Subnetwork {i+1}")
            descs.append(f"- Source nodes: {subG_sources}")
            descs.append(f"- Sink nodes: {subG_sinks}")
        return "\n".join(descs)
    
    def _attempt_connection_subnetworks(
        self,
        equations: List[str],
        subnetwork_description: str,
        system_prompt: str,
        rewrite_continuity_template: str,
        main_signaling_pathways: str = "unknown",
        expected_readouts: str = "unknown"
    ) -> Optional[List[str]]:
        """
        Attempt to connect subnetworks using LLM.

        Args:
            equations: List of reaction equations
            system_prompt: System prompt for LLM
            rewrite_continuity_template: Template for rewriting continuity
            main_signaling_pathways: Main signaling pathways description
            expected_readouts: Expected readouts description

        Returns:
            List of connected reaction equations or None if failed
        """
        rewrite_prompt = rewrite_continuity_template.format(
            equations="\n".join(equations),
            subnetworks=subnetwork_description,
            main_signaling_pathways=main_signaling_pathways,
            expected_readouts=expected_readouts
        ).strip()

        completion = self.client.chat.completions.create(
            model=self.config["planner_model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": rewrite_prompt}
            ],
            seed=self.config["seed"]
        )

        output_lines = completion.choices[0].message.content.split("\n")
        output_lines = [x.strip() for x in output_lines if x.strip() != ""]

        return output_lines if output_lines else None
    
    
    def validate_equations_connectivity(
        self,
        equations: Union[List[str], np.ndarray], 
        logger: Optional[BioMathForgeLogger] = None,
        expected_readouts: str = "unknown",
        main_signaling_pathways: str = "unknown",
        max_iter: int = 10
    ) -> Optional[List[str]]:
        """
        Iteratively validate and correct disconnected reaction networks using LLM.
        """
        if isinstance(equations, np.ndarray):
            equations = equations.tolist()

        logger = logger or BioMathForgeLogger("network_repair")
        logger.info(f"🔍 Starting connectivity validation for {len(equations)} reaction equations")

        for i in range(max_iter):
            logger.info(f"🔄 Connectivity check round {i+1}/{max_iter}")
            network_df = parse_lines_to_dataframe(equations)
            is_connected, sources, sinks = check_network_continuity(network_df, logger)

            if is_connected:
                logger.info("✅ Network continuity is maintained.")
                return equations

            logger.warning("⚠️ Network continuity is broken.")
            subnetwork_description = self.describe_subnetworks(sources, sinks)

            # プロンプト取得
            try:
                system_prompt = self.prompt_manager.get_prompt("system_prompt")
                rewrite_continuity_prompt = self.prompt_manager.get_prompt("rewrite_continuity_prompt")
            except KeyError as e:
                self.logger.error(f"Prompt not found: {e}")
                break
            
            # ネットワーク断絶の修正
            refined_equations = self._attempt_connection_subnetworks(
                equations, subnetwork_description,
                system_prompt, rewrite_continuity_prompt,
                main_signaling_pathways, expected_readouts
            )

            if refined_equations is None:
                logger.error("❌ Failed to connect subnetworks. Stopping validation.")
                return None
            else:
                equations = refined_equations
                validated_lines = self.validate_equations_format(equations, max_iterations=3)
                if validated_lines is None:
                    logger.error("❌ Integration failed during validation.")
                    return None
                equations = validated_lines
        logger.error("❌ Maximum iterations reached without achieving connectivity.")
        return None
