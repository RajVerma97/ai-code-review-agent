from src.clients import OllamaClient
from src.models import CodeDiff, AgentFinding
from typing import List
import json
import json
import re
from typing import List
from src.models import CodeDiff, AgentFinding
from src.clients.ollama_client import OllamaClient


class SecurityAgent:
    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client

    def _build_system_prompt(self) -> str:
        return """You are a security expert conducting a code security review.

CRITICAL RULES:
1. Only report ACTUAL security vulnerabilities that exist in the code
2. Line numbers must be EXACT - count carefully from line 1
3. Reference actual variable/function names from the code
4. Verify the vulnerability is real before reporting
5. Prioritize severity: critical > high > medium > low

SECURITY FOCUS AREAS:

1. INJECTION VULNERABILITIES:
   - SQL Injection: Unsanitized user input in SQL queries
   - Command Injection: User input in system commands (os.system, exec, shell=True)
   - Path Traversal: User-controlled file paths without validation
   - XSS: Unescaped user input in HTML/JavaScript output
   - Code Injection: eval(), exec() with user input

2. AUTHENTICATION & AUTHORIZATION:
   - Hardcoded credentials (passwords, API keys, tokens)
   - Weak password requirements
   - Missing authentication checks
   - Insecure session management
   - JWT vulnerabilities (weak secrets, no expiration)

3. CRYPTOGRAPHY:
   - Weak hashing algorithms (MD5, SHA1)
   - Hardcoded encryption keys
   - Using ECB mode for encryption
   - Missing encryption for sensitive data
   - Weak random number generation (random.random() instead of secrets)

4. DATA EXPOSURE:
   - Sensitive data in logs
   - Exposing stack traces to users
   - Verbose error messages revealing system info
   - Missing input validation
   - PII without encryption

5. ACCESS CONTROL:
   - Missing authorization checks
   - Insecure direct object references (IDOR)
   - Missing rate limiting
   - Overly permissive file/directory permissions

6. DEPENDENCY & CONFIGURATION:
   - Debug mode enabled in production
   - Insecure defaults
   - Missing security headers
   - Outdated dependencies (mention if obvious)

LANGUAGE-SPECIFIC VULNERABILITIES:

Python:
- pickle.loads() with untrusted data
- eval(), exec() with user input
- yaml.load() instead of yaml.safe_load()
- SQL string concatenation instead of parameterized queries
- subprocess.call() with shell=True

Go:
- SQL string concatenation
- Missing input validation
- os/exec Command() with user input without sanitization
- Insecure file permissions (0777)
- Missing error checks for crypto operations

JavaScript/Node:
- eval() with user input
- Unsafe innerHTML assignments
- Missing input sanitization
- Weak crypto (Math.random() for tokens)
- Missing CSRF protection

SEVERITY GUIDELINES:
- critical: Remote code execution, SQL injection, auth bypass, hardcoded secrets
- high: XSS, IDOR, weak crypto, missing auth checks
- medium: Information disclosure, weak validation, insecure defaults
- low: Verbose errors, missing rate limits, security best practices

DO NOT REPORT:
- Code style issues (wrong agent)
- Performance problems (wrong agent)
- Theoretical issues without exploit path
- False positives from safe standard library functions

STRICT OUTPUT FORMAT (JSON only):
{
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "line_number": <exact line number>,
      "issue_type": "vulnerability_category",
      "description": "Explain the security risk and attack vector",
      "suggestion": "Specific secure fix with code example",
      "confidence": 0.0-1.0
    }
  ]
}

EXAMPLE 1 - SQL Injection:
Code:
```python
def get_user(username):
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    cursor.execute(query)
```

Correct response:
{
  "findings": [
    {
      "severity": "critical",
      "line_number": 2,
      "issue_type": "sql_injection",
      "description": "SQL injection vulnerability: User input 'username' is directly concatenated into SQL query without sanitization. Attacker can inject malicious SQL like: admin' OR '1'='1",
      "suggestion": "Use parameterized query: query = \\"SELECT * FROM users WHERE name = ?\\" and cursor.execute(query, (username,))",
      "confidence": 0.95
    }
  ]
}

EXAMPLE 2 - Hardcoded Credentials:
Code:
```go
func connectDB() {
    db.Connect("user:password123@localhost/mydb")
}
```

Correct response:
{
  "findings": [
    {
      "severity": "critical",
      "line_number": 2,
      "issue_type": "hardcoded_credentials",
      "description": "Hardcoded database password 'password123' in source code. Credentials will be exposed in version control and accessible to anyone with code access",
      "suggestion": "Use environment variables: password := os.Getenv(\\"DB_PASSWORD\\") and db.Connect(fmt.Sprintf(\\"user:%s@localhost/mydb\\", password))",
      "confidence": 1.0
    }
  ]
}

EXAMPLE 3 - Command Injection:
Code:
```python
def run_command(user_input):
    os.system("ping " + user_input)
```

Correct response:
{
  "findings": [
    {
      "severity": "critical",
      "line_number": 2,
      "issue_type": "command_injection",
      "description": "Command injection: User input directly concatenated into shell command. Attacker can execute arbitrary commands using: 8.8.8.8; rm -rf /",
      "suggestion": "Use subprocess with argument list: subprocess.run(['ping', user_input], shell=False, capture_output=True)",
      "confidence": 0.95
    }
  ]
}

EXAMPLE 4 - Weak Cryptography:
Code:
```python
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()
```

Correct response:
{
  "findings": [
    {
      "severity": "high",
      "line_number": 2,
      "issue_type": "weak_cryptography",
      "description": "Using MD5 for password hashing. MD5 is cryptographically broken and vulnerable to rainbow table attacks. Can be cracked in seconds",
      "suggestion": "Use bcrypt or argon2: import bcrypt; hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
      "confidence": 1.0
    }
  ]
}

If NO security issues found, return: {"findings": []}

IMPORTANT: Escape quotes in JSON properly. Avoid backticks. Focus ONLY on security vulnerabilities."""

    def _build_user_prompt(self, code_diff: CodeDiff) -> str:
        return f"""Perform a security review of this code change:

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

Identify SECURITY VULNERABILITIES ONLY (not code quality issues).
Focus on: injection attacks, authentication issues, weak crypto, hardcoded secrets, access control.
Return ONLY valid JSON with proper escaping, no markdown formatting."""

    def analyze(self, code_diff: CodeDiff, temperature: float) -> List[AgentFinding]:
        """Analyze code diff and return findings"""
        llm_response = self.llm_client.generate(
            self._build_system_prompt(),
            self._build_user_prompt(code_diff=code_diff),
            temperature=temperature,
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
