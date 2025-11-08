# Sample Revisions Test Fixtures

This directory contains sample revision data for testing the method tracking analysis.

## Structure

Each revision directory follows the naming convention: `YYYYMMDD_HHMMSS_<hash>`

```
sample_revisions/
├── 20250101_100000_hash1/
│   ├── code_blocks.csv
│   └── clone_pairs.csv
├── 20250101_110000_hash2/
│   ├── code_blocks.csv
│   └── clone_pairs.csv
└── 20250101_120000_hash3/
    ├── code_blocks.csv
    └── clone_pairs.csv
```

## Revisions Timeline

1. **Revision 1** (2025-01-01 10:00:00)
   - 3 methods: block_a, block_b, block_c
   - Clone pairs: 2 pairs
     - block_a ↔ block_b (ngram: 75%)
     - block_b ↔ block_c (ngram: 65%, lcs: 72%)

2. **Revision 2** (2025-01-01 11:00:00)
   - 3 methods: block_a2, block_b2, block_d
   - Clone pairs: 2 pairs
     - block_a2 ↔ block_d (ngram: 80%)
     - block_b2 ↔ block_d (ngram: 55%, lcs: 68%)
   - Method transitions:
     - block_a → block_a2 (survived, unchanged, same token_hash)
     - block_b → block_b2 (survived, modified)
     - block_c → deleted
     - block_d → added

3. **Revision 3** (2025-01-01 12:00:00)
   - 3 methods: block_a3, block_d2, block_e
   - Clone pairs: 2 pairs
     - block_a3 ↔ block_d2 (ngram: 85%)
     - block_a3 ↔ block_e (ngram: 70%)
   - Method transitions:
     - block_a2 → block_a3 (survived, unchanged, same token_hash)
     - block_b2 → deleted
     - block_d → block_d2 (survived, unchanged, same token_hash)
     - block_e → added

## Usage

These fixtures are used by `test_revision_manager.py` to test:
- Revision detection and sorting
- Data loading (code_blocks, clone_pairs)
- Date range filtering
