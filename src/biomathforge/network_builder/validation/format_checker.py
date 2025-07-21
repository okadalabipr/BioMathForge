import re
from typing import List, Dict, Any, Optional, Union, Tuple

from biomathforge.shared.utils.logger import BioMathForgeLogger

class BioModelFormatValidator:
    """Text2Model format validation class"""

    def __init__(self,
                 logger: Optional[BioMathForgeLogger] = None,):
        self.patterns = self._initialize_patterns()
        self.logger = logger or BioMathForgeLogger("format_validator")

    def _initialize_patterns(self) -> List[re.Pattern]:
        """Initialize regex patterns for validating reaction equations"""
        return [
            # dimerize: "A dimerizes <--> A-A"
            re.compile(r'^\S+\s+dimerizes\s+<-->\s+\S+$'),
            # bind: "A binds B <--> A-B"
            re.compile(r'^\S+\s+binds\s+\S+\s+<-->\s+\S+$'),
            # dissociate: "A-B dissociates to A and B"
            re.compile(r'^\S+\s+dissociates\s+to\s+\S+\s+and\s+\S+$'),
            # phosphorylate: "B phosphorylates uA --> pA"
            re.compile(r'^\S+\s+phosphorylates\s+\S+\s+-->\s+\S+$'),
            # is phosphorylated: "uA is phosphorylated <--> pA"
            re.compile(r'^\S+\s+is\s+phosphorylated\s+<-->\s+\S+$'),
            # dephosphorylate: "B dephosphorylates pA --> uA"
            re.compile(r'^\S+\s+dephosphorylates\s+\S+\s+-->\s+\S+$'),
            # is dephosphorylated: "pA is dephosphorylated --> uA"
            re.compile(r'^\S+\s+is\s+dephosphorylated\s+-->\s+\S+$'),
            # transcribe: "B transcribes A"
            re.compile(r'^\S+\s+transcribes\s+\S+$'),
            # synthesize: "B synthesizes A"
            re.compile(r'^\S+\s+synthesizes\s+\S+$'),
            # is synthesized: "A is synthesized"
            re.compile(r'^\S+\s+is\s+synthesized$'),
            # degrade: "B degrades A"
            re.compile(r'^\S+\s+degrades\s+\S+$'),
            # is degraded: "A is degraded"
            re.compile(r'^\S+\s+is\s+degraded$'),
            # translocate: "Acyt translocates <--> Anuc"
            re.compile(r'^\S+\s+translocates\s+<-->\s+\S+$'),
            # activate: "A activates B"
            re.compile(r'^\S+\s+activates\s+\S+$'),
            # inhibit: "A inhibits B"
            re.compile(r'^\S+\s+inhibits\s+\S+$'),
            # state transition: "A <--> B"
            re.compile(r'^\S+\s+<-->\s+\S+$'),
            # @rxn format for Michaelis-Menten equations
            re.compile(r'^@rxn\s+.+-->\s*.+:\s*.+$'),
        ]

    def validate_line(self, line: str) -> bool:
        """
        Validate a single reaction equation line

        Args:
            line: The reaction equation line to validate

        Returns:
            bool: True if valid
        """
        if not line.strip():
            return False

        # パラメータ部分を除去 (| より後の部分)
        clean_line = line.split("|")[0].strip()

        # 各パターンで検証
        for pattern in self.patterns:
            if pattern.match(clean_line):
                return True

        return False

    def find_invalid_lines(self, text: str) -> List[str]:
        """
        Find invalid lines

        Args:
            text: Text to validate

        Returns:
            List[str]: List of invalid lines
        """
        invalid_lines = []

        for line in text.splitlines():
            line = line.strip()
            if not line:  # 空行はスキップ
                continue
            if not line.startswith('#'):  # コメント行はスキップ
                if not self.validate_line(line):
                    invalid_lines.append(line)

        return invalid_lines

    def check_format(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check the format and return results

        Args:
            text: Text to validate

        Returns:
            Tuple[bool, List[str]]: (overall validity, list of invalid lines)
        """
        invalid_lines = self.find_invalid_lines(text)
        is_valid = len(invalid_lines) == 0

        if is_valid:
            self.logger.info("✅ All reaction equations have valid format")
        else:
            self.logger.warning(f"⚠️ {len(invalid_lines)} lines with invalid format detected")

        return is_valid, invalid_lines