#!/bin/bash

# UK Gilts Data Processing Pipeline
# Connects download, data loading, and yield curve generation
# 
# Usage: ./run.sh [YYYY-MM-DD]
# Set TRADEWEB_USERNAME and TRADEWEB_PASSWORD environment variables for downloads

source .env

# Configuration
LOG_DIR="downloads/logs"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
TARGET_DATE="${1:-$(date +%Y-%m-%d)}"  # Use provided date or today

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== UK Gilts Data Pipeline Started ==="
log "Target date: $TARGET_DATE"
log "Log file: $LOG_FILE"

# Step 1: Download fresh data (optional - requires credentials)
if [[ -n "$TRADEWEB_USERNAME" && -n "$TRADEWEB_PASSWORD" ]]; then
    log "Step 1: Downloading fresh data from Tradeweb..."
    if python download.py >> "$LOG_FILE" 2>&1; then
        log "✅ Data download completed successfully"
    else
        log "❌ Data download failed (exit code: $?)"
        log "⚠️  Continuing with existing CSV files..."
    fi
else
    log "Step 1: Skipping download (credentials not provided)"
    log "ℹ️  Set TRADEWEB_USERNAME and TRADEWEB_PASSWORD to enable automatic downloads"
fi

# Step 2: Load bond data for target date
log "Step 2: Loading bond data for $TARGET_DATE..."
if python bond_data.py "$TARGET_DATE" >> "$LOG_FILE" 2>&1; then
    log "✅ Bond data loaded successfully"
    
    # Get database statistics
    TOTAL_BONDS=$(sqlite3 bonds.db "SELECT COUNT(*) FROM bonds WHERE business_date = '$TARGET_DATE';")
    TOTAL_DATES=$(sqlite3 bonds.db "SELECT COUNT(DISTINCT business_date) FROM bonds;")
    log "📊 Database stats: $TOTAL_BONDS bonds for $TARGET_DATE, $TOTAL_DATES total dates"
else
    log "❌ Bond data loading failed (exit code: $?)"
    log "🛑 Cannot proceed without bond data"
    exit 1
fi

# Step 3: Generate yield curve
YIELD_CURVE_DATE=$(date -d "$TARGET_DATE - 1 day" +%Y-%m-%d)
log "Step 3: Generating yield curve for $YIELD_CURVE_DATE (target minus 1 day)..."
if python yield_curve.py "$YIELD_CURVE_DATE" >> "$LOG_FILE" 2>&1; then
    log "✅ Yield curve generated successfully"
    
    # Get yield curve statistics
    CURVE_POINTS=$(sqlite3 bonds.db "SELECT COUNT(*) FROM yield_curves WHERE business_date = '$YIELD_CURVE_DATE';")
    log "📈 Yield curve: $CURVE_POINTS points generated"
else
    log "❌ Yield curve generation failed (exit code: $?)"
    log "⚠️  Bond data loaded but yield curve unavailable"
fi

# Step 4: Database health check
log "Step 4: Running database health check..."
BOND_COUNT=$(sqlite3 bonds.db "SELECT COUNT(*) FROM bonds;")
CURVE_COUNT=$(sqlite3 bonds.db "SELECT COUNT(*) FROM yield_curves;")
DATE_RANGE=$(sqlite3 bonds.db "SELECT MIN(business_date) || ' to ' || MAX(business_date) FROM bonds;")
UK_BONDS=$(sqlite3 bonds.db "SELECT COUNT(DISTINCT isin) FROM bonds WHERE isin LIKE 'GB%';")

log "📋 Database Health Check:"
log "   Total bonds: $BOND_COUNT"
log "   Total yield curve points: $CURVE_COUNT"
log "   Date range: $DATE_RANGE"
log "   Unique UK bonds: $UK_BONDS"

# Step 5: Check for potential issues
log "Step 5: Checking for data quality issues..."

# Check for missing yields
MISSING_YIELDS=$(sqlite3 bonds.db "SELECT COUNT(*) FROM bonds WHERE business_date = '$TARGET_DATE' AND yield IS NULL AND isin LIKE 'GB%';")
if [[ $MISSING_YIELDS -gt 0 ]]; then
    log "⚠️  Warning: $MISSING_YIELDS UK bonds missing yield data for $TARGET_DATE"
fi

# Check for old data
DAYS_OLD=$(sqlite3 bonds.db "SELECT julianday('now') - julianday(MAX(business_date)) FROM bonds;")
if (( $(echo "$DAYS_OLD > 7" | bc -l) )); then
    log "⚠️  Warning: Latest bond data is $DAYS_OLD days old"
fi

# Step 6: Generate summary report
log "Step 6: Generating summary report..."
SUMMARY_FILE="$LOG_DIR/summary_$(date +%Y%m%d).txt"

cat > "$SUMMARY_FILE" << EOF
UK Gilts Data Pipeline Summary
Generated: $(date)
Target Date: $TARGET_DATE

=== Data Overview ===
Total Bonds in Database: $BOND_COUNT
Total Yield Curve Points: $CURVE_COUNT
Date Range: $DATE_RANGE
Unique UK Bonds: $UK_BONDS

=== Latest Processing ===
Bonds for $TARGET_DATE: $TOTAL_BONDS
Yield Curve Points: $CURVE_POINTS
Missing Yields (UK): $MISSING_YIELDS

=== Bond Types for $TARGET_DATE ===
EOF

sqlite3 bonds.db "SELECT type, COUNT(*) as count FROM bonds WHERE business_date = '$TARGET_DATE' GROUP BY type ORDER BY count DESC;" >> "$SUMMARY_FILE"

log "📄 Summary report saved: $SUMMARY_FILE"

# Final status
if [[ $CURVE_POINTS -gt 0 && $TOTAL_BONDS -gt 0 ]]; then
    log "🎉 Pipeline completed successfully!"
    log "💡 Start web server with: python app.py"
    exit 0
else
    log "⚠️  Pipeline completed with warnings"
    exit 1
fi
