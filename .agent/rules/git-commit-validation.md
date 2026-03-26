---
paths:
  - ".git/hooks/pre-commit"
---
Pre-commit hook MUST be kept under 1479 characters. Validation includes checking .gitignore patterns and README documentation consistency. Hook execution runs automatically on git commit; any validation failure prevents commit until issues resolved. When patching LLM responses, always return complete objects with all properties to avoid partial match failures. For environment variable testing, use monkeypatch/os.environ manipulation for real-world usage verification.