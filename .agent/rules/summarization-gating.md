---
paths:
  - "src/sebba_code/memory/**"
  - "src/sebba_code/nodes/extract.py"
---
Use content-length threshold (50 chars) to gate L2→L1 summarization. Only L2 content above threshold triggers L1 generation to avoid trivial summaries.