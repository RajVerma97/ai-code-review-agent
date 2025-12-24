from src.clients import OllamaClient
from src.models import CodeDiff, AgentFinding
from typing import List
import json
import json
import re
from typing import List
from src.models import CodeDiff, AgentFinding
from src.clients.ollama_client import OllamaClient


class CodeQualityAgent:
    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client

    def _build_system_prompt(self) -> str:
        return """You are a senior software engineer reviewing code quality.

CRITICAL RULES:
1. Only report issues that ACTUALLY EXIST in the code
2. Line numbers must be EXACT - count carefully from line 1
3. Reference actual variable/function names from the code
4. DO NOT report non-existent errors (e.g., strings.Split in Go never returns errors)
5. Verify language-specific behavior before reporting issues

When analyzing code:
- Count lines carefully (line 1 = first line)
- Quote the exact problematic code element
- Explain WHY it's a problem for THIS specific code
- Provide a concrete, actionable fix
- VERIFY the issue exists in that language before reporting

Focus on REAL issues:
- Unclear naming (single letters: 'd', 'x', 'v')
- Missing documentation for exported functions
- Missing input validation (nil checks, empty strings, bounds)
- Actual error handling gaps (ignoring returned errors)
- NOT imaginary errors (like error handling for functions that don't return errors)

Language-Specific Knowledge:
- Go: strings.Split() never returns error, only a slice
- Go: fmt.Println() can be ignored in simple cases
- Python: str.split() never raises exception for basic usage
- Know the standard library before reporting issues

STRICT OUTPUT FORMAT (JSON only, use double quotes for strings):
{
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "line_number": <exact line number>,
      "issue_type": "brief_category",
      "description": "Quote the exact code element and explain the issue",
      "suggestion": "Specific fix with example code",
      "confidence": 0.0-1.0
    }
  ]
}

IMPORTANT: In your JSON response, escape all special characters properly:
- Use \\" for quotes inside strings
- Avoid using backticks - use plain text instead
- Keep suggestions clear and simple

EXAMPLE (Good findings):
Code: 
```go
func ProcessData(d string) {
    x := strings.Split(d, ",")
    for _, v := range x {
        fmt.Println(v)
    }
}
```

Correct response:
{
  "findings": [
    {
      "severity": "low",
      "line_number": 1,
      "issue_type": "unclear_naming",
      "description": "Parameter 'd' is unclear. Should be 'data' or 'csvString' to indicate it expects comma-separated values",
      "suggestion": "Rename to: func ProcessData(csvString string) or func ProcessData(data string)",
      "confidence": 0.9
    },
    {
      "severity": "low",
      "line_number": 2,
      "issue_type": "unclear_naming",
      "description": "Variable 'x' is unclear. Should be 'values' or 'parts' to indicate the split result",
      "suggestion": "Rename to: values := strings.Split(d, \\\",\\\")",
      "confidence": 0.9
    },
    {
      "severity": "low",
      "line_number": 3,
      "issue_type": "unclear_naming",
      "description": "Loop variable 'v' is unclear. Should be 'value' or 'part'",
      "suggestion": "Change to: for _, value := range x",
      "confidence": 0.8
    },
    {
      "severity": "low",
      "line_number": 1,
      "issue_type": "missing_documentation",
      "description": "Exported function ProcessData lacks documentation explaining its purpose and parameters",
      "suggestion": "Add comment: // ProcessData splits a comma-separated string and prints each value",
      "confidence": 0.7
    }
  ]
}

If NO issues, return: {"findings": []}"""

    def _build_user_prompt(self, code_diff: CodeDiff) -> str:
        return f"""Analyze this code change for quality issues:

File: {code_diff.file_path}
Language: {code_diff.language}

OLD CODE:
```{code_diff.language}
{code_diff.old_code}
```

NEW CODE:
```{code_diff.language}
{code_diff.new_code}
```

Identify code quality issues. Return ONLY valid JSON with proper escaping, no markdown formatting."""

    def analyze(self, code_diff: CodeDiff) -> List[AgentFinding]:
        """Analyze code diff and return findings"""
        llm_response = self.llm_client.generate(
            self._build_system_prompt(),
            self._build_user_prompt(code_diff=code_diff),
            temperature=0.3,
            max_tokens=1500,
        )
        return self._parse_response(llm_output=llm_response)

    def _clean_json_string(self, text: str) -> str:
        """Clean and prepare JSON string for parsing"""
        # Remove markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Try to extract JSON object if wrapped in other text
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            text = json_match.group(0)

        return text

    def _fix_json_quotes(self, text: str) -> str:
        """Replace smart quotes with regular quotes"""
        replacements = {
            '"': '"',  # Left double quote
            '"': '"',  # Right double quote
            """: "'",  # Left single quote
            """: "'",  # Right single quote
            "`": "'",  # Backtick to single quote
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _parse_response(self, llm_output: str) -> List[AgentFinding]:
        """Parse LLM JSON response into AgentFinding objects with robust error handling"""
        try:
            # Clean the output
            cleaned = self._clean_json_string(llm_output)
            cleaned = self._fix_json_quotes(cleaned)

            # Try to parse JSON
            data = json.loads(cleaned)
            findings = []

            for finding_data in data.get("findings", []):
                try:
                    finding = AgentFinding(
                        severity=finding_data.get("severity", "low"),
                        line_number=finding_data.get("line_number", 0),
                        issue_type=finding_data.get("issue_type", "unknown"),
                        description=finding_data.get("description", ""),
                        suggestion=finding_data.get("suggestion", ""),
                        confidence=float(finding_data.get("confidence", 0.5)),
                    )
                    findings.append(finding)
                except Exception as e:
                    print(f"[{self.llm_client.model_name}] Error parsing finding: {e}")
                    print(f"Finding data: {finding_data}")
                    continue

            return findings

        except json.JSONDecodeError as e:
            print(f"[{self.llm_client.model_name}] JSON parse error: {e}")
            print(f"Attempted to parse: {cleaned[:500]}...")

            # Fallback: try to extract findings manually
            return self._fallback_parse(llm_output)

        except Exception as e:
            print(f"[{self.llm_client.model_name}] Unexpected parsing error: {e}")
            return []

    def _fallback_parse(self, llm_output: str) -> List[AgentFinding]:
        """Fallback parser when JSON parsing fails"""
        findings = []

        # Try to extract individual findings using regex
        try:
            # Look for severity patterns
            severity_pattern = r'"severity":\s*"(\w+)"'
            line_pattern = r'"line_number":\s*(\d+)'
            issue_pattern = r'"issue_type":\s*"([^"]+)"'
            desc_pattern = r'"description":\s*"([^"]+)"'

            severities = re.findall(severity_pattern, llm_output)
            lines = re.findall(line_pattern, llm_output)
            issues = re.findall(issue_pattern, llm_output)
            descriptions = re.findall(desc_pattern, llm_output)

            # Create findings from matched patterns
            for i in range(
                min(len(severities), len(lines), len(issues), len(descriptions))
            ):
                finding = AgentFinding(
                    severity=severities[i],
                    line_number=int(lines[i]),
                    issue_type=issues[i],
                    description=descriptions[i],
                    suggestion="See description for details",
                    confidence=0.5,
                )
                findings.append(finding)

            if findings:
                print(
                    f"[{self.llm_client.model_name}] Fallback parser extracted {len(findings)} findings"
                )

        except Exception as e:
            print(f"[{self.llm_client.model_name}] Fallback parser error: {e}")

        return findings
