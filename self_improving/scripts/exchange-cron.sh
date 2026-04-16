#!/bin/bash
# Cold/Hot Exchange Cron Hook
# Run this via cron for automatic layer management

# After merge, Self-Improving is now inside FTS5 repo
SELF_IMPROVING_DIR="$HOME/.openclaw/skills/fts5/self_improving"
LOG_DIR="$HOME/.openclaw/logs"
LOG_FILE="$LOG_DIR/fts5_exchange.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Run exchange engine
python3 "$SELF_IMPROVING_DIR/scripts/exchange_engine.py" >> "$LOG_FILE" 2>&1

# Also run reindex
python3 "$SELF_IMPROVING_DIR/scripts/reindex.py" >> "$LOG_FILE" 2>&1

echo "Exchange cycle completed at $(date)" >> "$LOG_FILE"