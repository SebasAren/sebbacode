#!/bin/bash
# README-to-Source Consistency Audit Script
# Verifies environment variables documented in README.md match actual implementation

echo "=========================================="
echo "README-to-Source Consistency Audit"
echo "=========================================="
echo ""

# Track findings
ISSUES=0
PASSES=0

# Expected environment variables from README (lines 253-260)
EXPECTED_VARS="SEBBA_API_KEY SEBBA_MODEL SEBBA_MODEL_PROVIDER SEBBA_BASE_URL SEBBA_CHEAP_MODEL SEBBA_CHEAP_MODEL_PROVIDER SEBBA_CHEAP_BASE_URL SEBBA_CHEAP_API_KEY"

# Expected default values from README
SEBBA_MODEL_DEFAULT="claude-sonnet-4-6"
SEBBA_CHEAP_MODEL_DEFAULT="claude-haiku-4-5-20251001"

echo "1. Checking SEBBA_* variables in source files..."
echo ""

# Check each expected variable exists in config.py
for var in $EXPECTED_VARS; do
    if grep -q "\"$var\"" src/sebba_code/config.py; then
        echo "   ✓ $var found in config.py"
        PASSES=$((PASSES + 1))
    else
        echo "   ✗ $var MISSING from config.py"
        ISSUES=$((ISSUES + 1))
    fi
done

echo ""
echo "2. Checking SEBBA_* variables in llm.py..."
echo ""

# Check each expected variable exists in llm.py
for var in $EXPECTED_VARS; do
    if grep -q "\"$var\"" src/sebba_code/llm.py; then
        echo "   ✓ $var found in llm.py"
        PASSES=$((PASSES + 1))
    else
        echo "   ✗ $var MISSING from llm.py"
        ISSUES=$((ISSUES + 1))
    fi
done

echo ""
echo "3. Checking default model values..."
echo ""

# Verify defaults match README
config_model=$(grep -o '"claude-sonnet[^"]*"' src/sebba_code/config.py | head -1 | tr -d '"')
config_cheap=$(grep -o '"claude-haiku[^"]*"' src/sebba_code/config.py | head -1 | tr -d '"')
llm_model=$(grep -o '"claude-sonnet[^"]*"' src/sebba_code/llm.py | head -1 | tr -d '"')
llm_cheap=$(grep -o '"claude-haiku[^"]*"' src/sebba_code/llm.py | head -1 | tr -d '"')

if [ "$config_model" = "$SEBBA_MODEL_DEFAULT" ]; then
    echo "   ✓ SEBBA_MODEL default: $config_model (matches README)"
    PASSES=$((PASSES + 1))
else
    echo "   ✗ SEBBA_MODEL default MISMATCH: config.py has '$config_model', README expects '$SEBBA_MODEL_DEFAULT'"
    ISSUES=$((ISSUES + 1))
fi

if [ "$config_cheap" = "$SEBBA_CHEAP_MODEL_DEFAULT" ]; then
    echo "   ✓ SEBBA_CHEAP_MODEL default: $config_cheap (matches README)"
    PASSES=$((PASSES + 1))
else
    echo "   ✗ SEBBA_CHEAP_MODEL default MISMATCH: config.py has '$config_cheap', README expects '$SEBBA_CHEAP_MODEL_DEFAULT'"
    ISSUES=$((ISSUES + 1))
fi

echo ""
echo "4. Verifying README documentation for SEBBA_* variables..."
echo ""

# Find all SEBBA_* env vars in source
ALL_CODE_VARS=$(grep -roh "SEBBA_[A-Z_]*" src/sebba_code/ --include="*.py" 2>/dev/null | sort -u)
for var in $ALL_CODE_VARS; do
    # Check if this variable is documented in README env table
    if ! grep -q "$var" README.md; then
        echo "   ⚠ $var found in code but NOT documented in README"
        ISSUES=$((ISSUES + 1))
    else
        echo "   ✓ $var documented in README"
        PASSES=$((PASSES + 1))
    fi
done

echo ""
echo "=========================================="
echo "Audit Summary"
echo "=========================================="
echo "Passes: $PASSES"
echo "Issues Found: $ISSUES"
echo ""

if [ $ISSUES -eq 0 ]; then
    echo "✓ README is consistent with source files"
    exit 0
else
    echo "✗ Discrepancies found - see above for details"
    exit 1
fi
