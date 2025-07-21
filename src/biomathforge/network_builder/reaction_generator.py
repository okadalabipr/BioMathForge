import json
import time
import ast
import datetime
from typing import List, Optional, Dict, Any, Union
import pandas as pd
import numpy as np
from pathlib import Path

from openai import OpenAI

from biomathforge.shared.ai.prompt_manager import PromptManager
from biomathforge.shared.ai.response_handler import ResponseHandler
from biomathforge.shared.utils.logger import BioMathForgeLogger

class FormattedReactionGenerator:
    """Class for generating formatted reaction equations"""
    
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
            prompts_dir: Prompt directory
            prompt_manager: Prompt management instance
            config: Configuration dictionary
            logger: Logger instance
        """
        self.logger = logger or BioMathForgeLogger("reaction_generator")
        
        # AI client initialization
        # Note: Currently supports only the OpenAI API. Other LLM providers may be added in the future.
        # Assumes that the environment variable OPENAI_API_KEY is set using dotenv.
        self.client = openai_client or OpenAI()
        self.config = config or {"planner_model": "o3-2025-04-16", "writer_model": "o4-mini-2025-04-16", "seed": 42}
        
        # Initialize prompt manager
        self.prompt_manager = prompt_manager or PromptManager()
        
        # Initialize the response handler
        self.response_handler = ResponseHandler(
            openai_client=openai_client, 
            logger=logger, 
            prompt_manager=prompt_manager, 
            config=config
        )
    
    def prepare_biomodels_data(self, biomodels_reactions: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocessing of BioModels data
        
        Args:
            biomodels_reactions: Original BioModels DataFrame
            
        Returns:
            Preprocessed DataFrame
        """
        self.logger.info("📊 Preprocessing BioModels data...")
        
        required_cols = [
            "entity_gene_symbols", "entity_id", 
            "reaction with inferred entities", "rate with inferred entities",
            "reaction with entity labels", "rate with entity labels", 
            "parameters", "initial concentration/amount", "model", "count"
        ]
        
        available_cols = [col for col in required_cols if col in biomodels_reactions.columns]
        processed_df = biomodels_reactions[available_cols].copy()
        
        for col in available_cols:
            if col in ["entity_gene_symbols", "count"]:
                continue
            
            if col in processed_df.columns:
                try:
                    processed_df[col] = processed_df[col].apply(
                        lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️  Error converting column {col}: {e}")
        
        self.logger.info(f"✅ Successfully preprocessed {len(processed_df)} rows of data")
        return processed_df
    
    def create_reaction_table(self, row: pd.Series) -> str:
        """
        Create a reaction table in Markdown format
        
        Args:
            row: A single row of the DataFrame
            
        Returns:
            Reaction table in Markdown format
        """
        reaction_data = []
        
        reaction_cols = ["reaction with inferred entities", "rate with inferred entities"]
        
        for col in reaction_cols:
            if col in row.index and row[col] is not None:
                if isinstance(row[col], (list, np.ndarray)):
                    reaction_data.append(row[col])
                else:
                    reaction_data.append([row[col]])
        
        if not reaction_data or len(reaction_data) < 2:
            return "| Reaction | Rate Equation |\n|----------|---------------|\n| No data | No data |"
        
        # Create a DataFrame
        max_length = max(len(data) for data in reaction_data)
        
        # Align lengths
        for i, data in enumerate(reaction_data):
            if len(data) < max_length:
                reaction_data[i].extend([''] * (max_length - len(data)))
        
        df = pd.DataFrame(reaction_data).T
        df.columns = ["Reaction", "Rate Equation"]
        
        return df.to_markdown(index=False)
    
    def generate_batch_reactions(
        self, 
        biomodels_reactions: pd.DataFrame,
        max_rows: int = 30,
        use_batch_api: bool = True
    ) -> List[str]:
        """
        Reaction generation using the batch API
        
        Args:
            biomodels_reactions: BioModels data
            max_rows: Maximum number of rows to process
            use_batch_api: Whether to use the batch API
            
        Returns:
            List of generated reactions
        """
        self.logger.info(f"🚀 Starting batch reaction generation (up to {max_rows} rows)")
        
        # データ前処理
        processed_data = self.prepare_biomodels_data(biomodels_reactions)
        
        # 処理対象行を制限
        target_rows = processed_data.iloc[:max_rows]
        
        # プロンプト取得
        system_prompt = self.prompt_manager.get_prompt("system_prompt")
        generation_template = self.prompt_manager.get_prompt("generation_prompt")
        
        if not system_prompt or not generation_template:
            self.logger.error("❌ Prompts not found")
            return []
        
        # バッチリクエスト準備
        batch_requests = []
        
        for i, (_, row) in enumerate(target_rows.iterrows()):
            genes = row.get("entity_gene_symbols", "")
            reference_table = self.create_reaction_table(row)
            
            # 生成プロンプト作成
            user_prompt = generation_template.format(
                genes=genes,
                reference_tbl=reference_table
            ).strip()
            
            request = {
                "custom_id": f"request_{i}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": self.config["planner_model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_completion_tokens": 100000,
                    "seed": self.config["seed"],
                }
            }
            batch_requests.append(request)
        
        # バッチAPI実行
        if use_batch_api and len(batch_requests) > 1:
            return self._execute_batch_api(batch_requests, target_rows)
        else:
            return self._execute_individual_requests(batch_requests, target_rows)
    
    def _execute_batch_api(
        self, 
        batch_requests: List[Dict], 
        target_rows: pd.DataFrame
    ) -> List[str]:
        """Execution of the batch API"""
        
        self.logger.info("📤 Sending batch API request...")
        
        # Create batch file
        batch_file_path = f"temp_batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        try:
            with open(batch_file_path, "w") as f:
                for request in batch_requests:
                    f.write(json.dumps(request) + "\n")
            
            # Upload batch file
            batch_input_file = self.client.files.create(
                file=open(batch_file_path, "rb"),
                purpose="batch"
            )
            
            # Create batch
            batch = self.client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"description": "BioMathForge reaction generation"}
            )
            
            self.logger.info(f"📊 バッチID: {batch.id}")
            self.logger.info("⏳ バッチ処理完了を待機中...")
            
            # Wait for batch completion
            while True:
                batch = self.client.batches.retrieve(batch.id)
                self.logger.info(f"📊 バッチステータス: {batch.status}")
                
                if batch.status == "completed":
                    break
                elif batch.status in ["failed", "expired", "cancelled"]:
                    self.logger.error(f"❌ バッチ処理失敗: {batch.status}")
                    return []
                
                time.sleep(300)  # Check at 300-second intervals
            
            # Retrieve results
            file_response = self.client.files.content(batch.output_file_id)
            return self._process_batch_response(file_response.text, target_rows)
            
        finally:
            # Delete temporary file
            if Path(batch_file_path).exists():
                Path(batch_file_path).unlink()
    
    def _execute_individual_requests(
        self, 
        batch_requests: List[Dict], 
        target_rows: pd.DataFrame
    ) -> List[str]:
        """Execution of individual requests"""
        
        self.logger.info("🔄 Generating reaction equations using individual requests...")
        
        all_reactions = []
        
        for i, request in enumerate(batch_requests):
            try:
                self.logger.info(f"📤 Sending request {i+1}/{len(batch_requests)}...")
                
                # API call
                completion = self.client.chat.completions.create(
                    **request["body"]
                )
                
                content = completion.choices[0].message.content
                
                # Add gene information
                gene_info = target_rows.iloc[i].get("entity_gene_symbols", f"request_{i}")
                
                # Store with gene information
                contents = [f"{gene_info}\t" + c for c in content.split("\n")]
                all_reactions.extend(contents)
                
                # Rate limiting measures
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in request {i+1}: {e}")
                continue
        
        return all_reactions
    
    def _process_batch_response(self, response_text: str, target_rows: pd.DataFrame) -> List[str]:
        """Processing the batch API response"""
        
        self.logger.info("📥 Processing batch response...")
        
        all_reactions = []
        
        for i, line in enumerate(response_text.strip().split("\n")):
            try:
                response_data = json.loads(line)
                content = response_data["response"]["body"]["choices"][0]["message"]["content"]
                
                # Retrieve gene information
                gene_info = target_rows.iloc[i].get("entity_gene_symbols", f"batch_{i}")
                
                # Store with gene information
                contents = [f"{gene_info}\t" + c for c in content.split("\n")]
                all_reactions.extend(contents)
                    
            except Exception as e:
                self.logger.error(f"❌ Error processing response {i+1}: {e}")
                continue
        
        self.logger.info(f"✅ Successfully generated {len(all_reactions)} reaction equations")
        return all_reactions
    


def generate_formatted_reactions(
    biomodels_reactions: pd.DataFrame,
    max_rows: int = 30,
    openai_client: Optional[OpenAI] = None,
    prompt_manager: Optional[PromptManager] = None,
    config: Optional[Dict[str, Any]] = None,
    use_batch_api: bool = True,
    validate_format: bool = True,
    max_iterations: int = 3,
    logger: Optional[BioMathForgeLogger] = None
) -> Optional[List[str]]:
    """
    Generate formatted reaction equations from BioModels data
    
    Args:
        biomodels_reactions: BioModels DataFrame
        max_rows: Maximum number of rows to process
        openai_client: OpenAI client (automatically created from environment variables if not specified)
        prompt_manager: Prompt management instance
        config: Configuration dictionary
        use_batch_api: Whether to use the batch API
        validate_format: Whether to perform format validation
        max_iterations: Maximum number of corrections (not used)
        logger: Logger instance
        
    Returns:
        List of validated reaction equations (None if failed)
    """
    logger = logger or BioMathForgeLogger("generate_formatted_reactions")
    
    try:
        # Initialize the generator
        generator = FormattedReactionGenerator(
            openai_client=openai_client,
            prompt_manager=prompt_manager,
            config=config,
            logger=logger
        )
        
        # 1. Reaction generation
        logger.info("🧬 反応式生成フェーズ開始")
        raw_reactions = generator.generate_batch_reactions(
            biomodels_reactions=biomodels_reactions,
            max_rows=max_rows,
            use_batch_api=use_batch_api
        )
        
        if not raw_reactions:
            logger.error("❌ 反応式生成に失敗しました")
            return None
        
        # 2. Format validation and correction
        if validate_format:
            logger.info("🔍 反応式検証フェーズ開始")
            
            # Extract reaction equations from tab-delimited data
            equations_only = []
            for reaction in raw_reactions:
                if "\t" in reaction:
                    _, equation = reaction.split("\t", 1)
                    equations_only.append(equation)
                else:
                    equations_only.append(reaction)
            
            # Validate and correct using ResponseHandler
            validated_reactions = generator.response_handler.validate_equations_format(equations_only, max_iterations=max_iterations)
            
            if validated_reactions is None:
                logger.warning("⚠️  検証に失敗しましたが、生の反応式を返します")
                # Extract reaction equations from tab-delimited data
                return equations_only
            
            return validated_reactions
        else:
            logger.info("ℹ️  検証をスキップします")
            # Extract reaction equations from tab-delimited data
            return [r.split("\t", 1)[1] if "\t" in r else r for r in raw_reactions]
    
    except Exception as e:
        logger.error(f"❌ An error occurred during reaction generation: {e}")
        return None
