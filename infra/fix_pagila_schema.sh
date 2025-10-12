#!/bin/bash
set -e

echo "==> Fixing Pagila schema for PostgreSQL 16 compatibility..."

# Files to patch
FILES=(
    "/opt/pagila/pagila-schema.sql"
    "/docker-entrypoint-initdb.d/02_pagila-schema.sql"
)

for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "==> Patching $file"
        
        # Remove transaction_timeout (not supported in some PostgreSQL versions)
        sed -i '/SET transaction_timeout/d' "$file"
        
        # Replace postgres user with pagila user
        sed -i 's/OWNER TO postgres;/OWNER TO pagila;/g' "$file"
        
        # Remove the problematic JSON_TABLE view and its ALTER statement
        # This is a more robust approach that handles multi-line statements
        awk '
        BEGIN { in_problem_view = 0 }
        /CREATE VIEW.*films_per_customer_rental/ { in_problem_view = 1; next }
        /ALTER VIEW.*films_per_customer_rental/ { next }
        in_problem_view && /^$/ { in_problem_view = 0; next }
        in_problem_view { next }
        { print }
        ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
        
        echo "==> Successfully patched $file"
    else
        echo "==> Warning: $file not found, skipping"
    fi
done

# Also patch data files for user references
DATA_FILES=(
    "/opt/pagila/pagila-data.sql"
    "/docker-entrypoint-initdb.d/03_pagila-data.sql"
)

for file in "${DATA_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "==> Patching data file $file"
        sed -i 's/OWNER TO postgres;/OWNER TO pagila;/g' "$file"
    fi
done

echo "==> Pagila schema patching complete!"