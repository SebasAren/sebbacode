---
paths:
  - "**/*.md"
  - "README.md"
  - "src/sebba_code/**/*.py"
---
# Documentation Standards

## Format
All project documentation in Markdown. README.md sections: Overview, Installation, Quick Start, Configuration, Roadmap, Memory Architecture, Rules System, Agent Tools, Architecture, Development, Project Structure, Dependencies, Design Influences.

## API Keys & Security
Never commit real API keys or credentials in documentation or code. Replace any exposed keys with placeholders (e.g., `your-api-key-here`).

## CLI Documentation Audit
When auditing CLI documentation: grep against `src/sebba_code/cli.py` to verify all flags (`--dry-run`, `--auto-approve`, `--max-todos`, `--verbose`, etc.) are documented in the CLI Reference section.

## Tool References
When documenting tool references, verify they exist in source code — non-existent tool references are a common documentation gap found during audits.

## Undocumented Features
When a design document references a feature not implemented in code:
1. Create audit entry with severity classification (HIGH: blocks core workflow / MEDIUM: incomplete implementation / LOW: undocumented config)
2. Add TODO in relevant source file referencing the audit
3. Update README.md if the feature is user-facing
