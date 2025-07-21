from pathlib import Path
from typing import Dict, Any
import yaml

from biomathforge.pathway_analyzer.prompts import (
    query_writer_instructions,
    section_writer_instructions,
    readout_evaluation_instructions,
    readout_refinement_instructions,
    feedback_crosstalk_query_writer,
    reaction_enhancement_prompt
)
from biomathforge.network_builder.prompts.system_prompts import (
    system_prompt
)
from biomathforge.network_builder.prompts.generation_prompts import (
    generation_prompt_template,
    rewrite_prompt_template
)
from biomathforge.network_builder.prompts.integration_prompts import (
    integrate_model_prompt_template,
    drop_duplicate_template,
    rewrite_continuity_template
)
from biomathforge.network_builder.prompts.finalization_prompts import (
    prevent_divergence_template,
    rewrite_activation_inhibition_template
)


class PromptManager:    
    def __init__(self):
        self._initialize_prompts()
    
    def _initialize_prompts(self):
        self._prompts = {
            "system_prompt": system_prompt.strip(),
            "generation_prompt": generation_prompt_template.strip(),
            "rewrite_prompt": rewrite_prompt_template.strip(),
            "integrate_model_prompt": integrate_model_prompt_template.strip(),
            "drop_duplicate_prompt": drop_duplicate_template.strip(),
            "rewrite_continuity_prompt": rewrite_continuity_template.strip(),
            "prevent_divergence_prompt": prevent_divergence_template.strip(),
            "rewrite_activation_inhibition_prompt": rewrite_activation_inhibition_template.strip(),
            "feedback_crosstalk_query_writer": feedback_crosstalk_query_writer.strip(),
            "section_writer_instructions": section_writer_instructions.strip(),
            "readout_evaluation_instructions": readout_evaluation_instructions.strip(),
            "readout_refinement_instructions": readout_refinement_instructions.strip(),
            "query_writer_instructions": query_writer_instructions.strip(),
            "reaction_enhancement_prompt": reaction_enhancement_prompt.strip()
        }
    
    def update_prompts_from_yaml(self, prompts_file: str):
        with open(prompts_file, 'r', encoding='utf-8') as f:
            self._prompts.update(yaml.safe_load(f))
    
    def update_prompt_from_dict(self, prompts_dict: Dict[str, Any]):
        self._prompts.update(prompts_dict)
    
    def update_prompt_from_txt(self, name: str, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            self._prompts[name] = f.read().strip()
    
    def update_prompt_from_text(self, name: str, text: str):
        self._prompts[name] = text

    def get_prompt(self, name: str) -> str:
        return self._prompts.get(name, "")