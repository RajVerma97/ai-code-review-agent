from src.clients import OllamaClient
from src.models import CodeDiff, AgentFinding
from typing import List
import json
import json
import re
from typing import List
from src.models import CodeDiff, AgentFinding
from src.clients.ollama_client import OllamaClient
from .base_agent import BaseAgent


class CodeQualityAgent(BaseAgent):
    temperature = 0.3

    def _get_agent_name(self) -> str:
        return "quality_agent"

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
