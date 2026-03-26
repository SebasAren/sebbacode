---
paths:
  - "src/sebba_code/memory/**"
  - "src/sebba_code/nodes/extract.py"
  - "src/sebba_code/helpers/memory_ops.py"
---
Memory extraction layer must write only to L2. Do not write directly to L1 from extraction code—use the condensation pipeline for L1 population.