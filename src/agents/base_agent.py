from src.clients import OllamaClient
from src.models import CodeDiff, AgentFinding
from typing import List
import json
import json
import re
from typing import List
from src.models import CodeDiff, AgentFinding
from src.clients.ollama_client import OllamaClient
from abc import abstractmethod, ABC


class BaseAgent(ABC):
    temperature: float

    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client

    @abstractmethod
    def _build_system_prompt(self) -> str:
        pass

    @abstractmethod
    def _build_user_prompt(self, code_diff: CodeDiff) -> str:
        pass

    @abstractmethod
    def _get_agent_name(self) -> str:
        pass

    def analyze(self, code_diff: CodeDiff) -> List[AgentFinding]:
        """Analyze code diff and return findings"""
        print(
            "agent is ",
            self._get_agent_name(),
            "temperature is ",
            self.temperature,
        )
        llm_response = self.llm_client.generate(
            self._build_system_prompt(),
            self._build_user_prompt(code_diff=code_diff),
            temperature=self.temperature,
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
