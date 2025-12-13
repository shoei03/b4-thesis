"""LLM-based feature extraction for method deletion prediction."""

from dataclasses import asdict, dataclass
import json
import os
from typing import Any

import anthropic


@dataclass
class CodeFeatures:
    """Features extracted from code by LLM."""

    # Semantic features
    purpose: str  # What the code does
    complexity_level: str  # simple/moderate/complex
    abstraction_level: str  # low/medium/high

    # Code quality indicators
    has_documentation: bool
    has_type_hints: bool
    code_smell_indicators: list[str]  # List of detected code smells

    # Refactoring indicators
    is_helper_function: bool
    is_duplicative: bool  # Duplicates logic elsewhere
    could_be_inlined: bool  # Could be merged into caller

    # Contextual clues
    usage_pattern: str  # how it's likely used
    deletion_likelihood: str  # low/medium/high
    deletion_reasons: list[str]  # Why it might be deleted

    # Raw analysis
    detailed_analysis: str  # Full contextual analysis


class LLMFeatureExtractor:
    """Extract features from code using LLM analysis."""

    def __init__(self, api_key: str | None = None):
        """Initialize extractor with API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_method(
        self,
        code: str,
        function_name: str,
        file_path: str,
        is_deleted: bool,
        clone_context: str = "",
    ) -> CodeFeatures:
        """Analyze a single method and extract features."""
        prompt = self._build_analysis_prompt(
            code, function_name, file_path, is_deleted, clone_context
        )

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        response_text = response.content[0].text
        features = self._parse_response(response_text)

        return features

    def _build_analysis_prompt(
        self,
        code: str,
        function_name: str,
        file_path: str,
        is_deleted: bool,
        clone_context: str = "",
    ) -> str:
        """Build analysis prompt for LLM."""
        status = "was deleted in a later revision" if is_deleted else "survived"

        return f"""You are analyzing Python code to understand features that predict method deletion.

**Method Information:**
- Function: `{function_name}`
- File: `{file_path}`
- Status: This method **{status}**
{f"- Clone Context: {clone_context}" if clone_context else ""}

**Code:**
```python
{code}
```

**Task:**
Analyze this code deeply and provide a structured analysis in JSON format. Consider:

1. **Semantic Features:**
   - What is the purpose of this code? (1-2 sentences)
   - Complexity level: simple/moderate/complex
   - Abstraction level: low/medium/high

2. **Code Quality:**
   - Has documentation (docstring)? true/false
   - Has type hints? true/false
   - Code smell indicators (list any detected)

3. **Refactoring Indicators:**
   - Is this a helper function (small, single-purpose)? true/false
   - Is this duplicative (duplicates logic elsewhere)? true/false
   - Could this be inlined (merged into caller)? true/false

4. **Contextual Analysis:**
   - How is this code likely used?
   - Deletion likelihood: low/medium/high (considering code patterns)
   - Possible deletion reasons (list)

5. **Detailed Analysis:**
   - Provide deeper contextual insights about why this code might or might not be deleted
   - Consider: complexity, maintainability, design patterns, coupling, cohesion

**Output Format (JSON):**
```json
{{
  "purpose": "...",
  "complexity_level": "simple|moderate|complex",
  "abstraction_level": "low|medium|high",
  "has_documentation": true|false,
  "has_type_hints": true|false,
  "code_smell_indicators": ["...", "..."],
  "is_helper_function": true|false,
  "is_duplicative": true|false,
  "could_be_inlined": true|false,
  "usage_pattern": "...",
  "deletion_likelihood": "low|medium|high",
  "deletion_reasons": ["...", "..."],
  "detailed_analysis": "..."
}}
```

Provide ONLY the JSON output, no additional text."""

    def _parse_response(self, response_text: str) -> CodeFeatures:
        """Parse LLM response into CodeFeatures."""
        # Extract JSON from response
        try:
            # Try to find JSON block
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                # Find first { and last }
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            data = json.loads(json_text)

            return CodeFeatures(
                purpose=data.get("purpose", "Unknown"),
                complexity_level=data.get("complexity_level", "moderate"),
                abstraction_level=data.get("abstraction_level", "medium"),
                has_documentation=data.get("has_documentation", False),
                has_type_hints=data.get("has_type_hints", False),
                code_smell_indicators=data.get("code_smell_indicators", []),
                is_helper_function=data.get("is_helper_function", False),
                is_duplicative=data.get("is_duplicative", False),
                could_be_inlined=data.get("could_be_inlined", False),
                usage_pattern=data.get("usage_pattern", "Unknown"),
                deletion_likelihood=data.get("deletion_likelihood", "medium"),
                deletion_reasons=data.get("deletion_reasons", []),
                detailed_analysis=data.get("detailed_analysis", ""),
            )

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            print(f"Response: {response_text[:200]}...")

            # Return default features
            return CodeFeatures(
                purpose="Parse error",
                complexity_level="moderate",
                abstraction_level="medium",
                has_documentation=False,
                has_type_hints=False,
                code_smell_indicators=["parse_error"],
                is_helper_function=False,
                is_duplicative=False,
                could_be_inlined=False,
                usage_pattern="Unknown",
                deletion_likelihood="medium",
                deletion_reasons=["Parse error occurred"],
                detailed_analysis=f"Failed to parse: {response_text[:200]}",
            )


def test_extractor():
    """Test the feature extractor with a sample."""
    # Sample deleted method from the reports
    code = """def _maybe_str_to_time_stamp(key, lev):
    if lev.is_all_dates and not isinstance(key, Timestamp):
        try:
            return Timestamp(key, tz=getattr(lev, 'tz', None))
        except Exception:
            pass
    return key"""

    extractor = LLMFeatureExtractor()

    print("Analyzing sample deleted method...")
    features = extractor.analyze_method(
        code=code,
        function_name="_maybe_str_to_time_stamp",
        file_path="pandas/core/indexes/multi.py",
        is_deleted=True,
        clone_context="Part of clone group with 3 members, match_type: similarity_moved",
    )

    print("\n--- Extracted Features ---")
    print(json.dumps(asdict(features), indent=2))


if __name__ == "__main__":
    test_extractor()
