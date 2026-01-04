#!/bin/bash

# API Environment Setup Script
echo "=== API Credentials Setup ==="
echo ""
echo "⚠️  IMPORTANT: Your previous Fitbit client secret was exposed and should be regenerated!"
echo "   1. Go to https://dev.fitbit.com/apps"
echo "   2. Find your 'PersonalDataSync' app"
echo "   3. Click 'Reset Client Secret'"
echo ""

# Get Fitbit credentials
echo "=== Fitbit API Credentials ==="
read -p "Fitbit Client ID: " FITBIT_CLIENT_ID
read -s -p "Fitbit Client Secret: " FITBIT_CLIENT_SECRET && echo
echo ""

# Get FatSecret credentials
echo "=== FatSecret API Credentials ==="
echo "If you need FatSecret credentials:"
echo "   1. Go to https://platform.fatsecret.com/api/"
echo "   2. Register and get your Consumer Key/Secret"
echo ""
read -p "FatSecret Consumer Key (optional): " FATSECRET_CLIENT_ID
read -s -p "FatSecret Consumer Secret (optional): " FATSECRET_CLIENT_SECRET && echo
echo ""

# Get database URL
read -p "Neon Database URL (optional): " NEON_DB_URL

# Add to .env.local file (append, don't overwrite existing Next.js vars)
if [ ! -f .env.local ]; then
    echo "# Next.js Environment Variables" > .env.local
fi

# Remove any existing API credentials
sed -i '/^FITBIT_CLIENT_ID=/d' .env.local 2>/dev/null || true
sed -i '/^FITBIT_CLIENT_SECRET=/d' .env.local 2>/dev/null || true
sed -i '/^FATSECRET_CLIENT_ID=/d' .env.local 2>/dev/null || true
sed -i '/^FATSECRET_CLIENT_SECRET=/d' .env.local 2>/dev/null || true
sed -i '/^NEON_DB_URL=/d' .env.local 2>/dev/null || true

# Add new credentials
echo "" >> .env.local

# Fitbit credentials
echo "# Fitbit API Credentials" >> .env.local
echo "FITBIT_CLIENT_ID=$FITBIT_CLIENT_ID" >> .env.local
echo "FITBIT_CLIENT_SECRET=$FITBIT_CLIENT_SECRET" >> .env.local

# FatSecret credentials (if provided)
if [ ! -z "$FATSECRET_CLIENT_ID" ] && [ ! -z "$FATSECRET_CLIENT_SECRET" ]; then
    echo "" >> .env.local
    echo "# FatSecret API Credentials" >> .env.local
    echo "FATSECRET_CLIENT_ID=$FATSECRET_CLIENT_ID" >> .env.local
    echo "FATSECRET_CLIENT_SECRET=$FATSECRET_CLIENT_SECRET" >> .env.local
fi

# Database URL (if provided)
if [ ! -z "$NEON_DB_URL" ]; then
    echo "" >> .env.local
    echo "# Database URL" >> .env.local
    echo "NEON_DB_URL=$NEON_DB_URL" >> .env.local
fi

# Make sure .env.local is gitignored
grep -q "^\.env\.local$" .gitignore 2>/dev/null || echo ".env.local" >> .gitignore

echo ""
echo "✓ Added API credentials to .env.local"
echo "✓ Updated .gitignore"
echo ""
echo "Now you can run:"
echo "  python fitbit_integration.py      # Sync Fitbit data"
if [ ! -z "$FATSECRET_CLIENT_ID" ]; then
    echo "  python fatsecret_migration.py     # Sync FatSecret data"
    echo "  python fatsecret_backfill.py      # Backfill FatSecret data"
fi
echo ""
echo "🔒 Remember to regenerate your Fitbit client secret on dev.fitbit.com!"