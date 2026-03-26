---
paths:
  - "src/sebba_code/nodes/*.py"
  - "src/sebba_code/*.py"
---
Memory writes (L1/L2) distributed across node implementations: context.py, rules.py, deepening.py. Memory/ dir is empty/deprecated. Extraction writes to L2 only—L1 summarization handled by async condensation pipeline.