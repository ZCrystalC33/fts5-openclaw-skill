#!/bin/bash
# Cold/Hot Exchange Cron Hook
# Run this via cron for automatic layer management

SELF_IMPROVING_DIR="$HOME/self-improving"
LOG_FILE="$HOME/self-improving/logs/exchange.log"

# Run exchange engine
python3 "$SELF_IMPROVING_DIR/scripts/exchange_engine.py" >> "$LOG_FILE" 2>&1

# Also run reindex
python3 "$SELF_IMPROVING_DIR/scripts/reindex.py" >> "$LOG_FILE" 2>&1

echo "Exchange cycle completed at $(date)" >> "$LOG_FILE"