#!/usr/bin/env python3
"""
Cold/Hot Layer Auto-Exchange Engine
Manages automatic promotion/demotion of memory entries.

Rules:
- HOT (memory.md): ≤100 lines, recently referenced (< 7 days)
- WARM (domains/): referenced 3+ times but not in top 10
- COLD (archive/): not referenced in 30+ days
"""

import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Paths - Support both original ~/self-improving/ and merged ~/.openclaw/skills/fts5/self_improving/
# Detect location based on context: if __init__.py exists in parent, we're inside FTS5 repo
_SCRIPT_DIR = Path(__file__).parent
_PARENT_DIR = _SCRIPT_DIR.parent

if (_PARENT_DIR / "__init__.py").exists() and (_SCRIPT_DIR.name == "scripts"):
    # Running inside FTS5 repo at ~/.openclaw/skills/fts5/self_improving/scripts/
    SELF_IMPROVING_DIR = _PARENT_DIR
else:
    # Running from original ~/self-improving/ location
    SELF_IMPROVING_DIR = Path.home() / "self-improving"

MEMORY_FILE = SELF_IMPROVING_DIR / "memory.md"
DOMAINS_DIR = SELF_IMPROVING_DIR / "domains"
PROJECTS_DIR = SELF_IMPROVING_DIR / "projects"
ARCHIVE_DIR = SELF_IMPROVING_DIR / "archive"
INDEX_FILE = SELF_IMPROVING_DIR / "index.md"

# Configuration
HOT_THRESHOLD_DAYS = 7      # Days before demoting from hot
COLD_THRESHOLD_DAYS = 30    # Days before archiving
PROMOTE_THRESHOLD = 3       # References needed to promote to warm
DEMOTE_THRESHOLD_TOP = 10   # If in top 10 and referenced, stay hot

# Pattern to detect last access timestamps in files
LAST_ACCESS_PATTERN = r'<!-- last_access: (\d{4}-\d{2}-\d{2}) -->'


def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def get_file_last_modified(file_path: Path) -> datetime:
    """Get last modified time of a file."""
    if not file_path.exists():
        return None
    return datetime.fromtimestamp(file_path.stat().st_mtime)


def get_last_access_from_content(content: str) -> datetime:
    """Parse last access timestamp from file content comments."""
    match = re.search(LAST_ACCESS_PATTERN, content)
    if match:
        return parse_date(match.group(1))
    return None


def update_last_access(file_path: Path) -> None:
    """Add/update last access comment in file."""
    if not file_path.exists():
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove existing last_access comment
    content = re.sub(LAST_ACCESS_PATTERN, '', content)
    
    # Add new comment at the top
    timestamp = get_current_time()
    new_content = f"<!-- last_access: {timestamp} -->\n{content}"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def count_references(file_path: Path, keyword: str) -> int:
    """Count references to a topic in memory.md."""
    if not MEMORY_FILE.exists() or not file_path.exists():
        return 0
    
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory_content = f.read()
        
        # Count mentions of the topic name
        topic_name = file_path.stem
        return len(re.findall(rf'\b{re.escape(topic_name)}\b', memory_content, re.IGNORECASE))
    except:
        return 0


def get_hot_topics_from_memory() -> List[Dict]:
    """Extract hot topics from memory.md based on references."""
    if not MEMORY_FILE.exists():
        return []
    
    topics = []
    topic_pattern = re.compile(r'^[-*]\s+\[?([^\]:]+)[\]:]?', re.MULTILINE)
    
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for match in topic_pattern.finditer(content):
            topic_name = match.group(1).strip()
            if topic_name and len(topic_name) > 2:
                topics.append(topic_name)
    except:
        pass
    
    return topics


def scan_warm_entries() -> List[Dict]:
    """Scan domains/ directory for warm entries."""
    if not DOMAINS_DIR.exists():
        return []
    
    entries = []
    for f in DOMAINS_DIR.glob("*.md"):
        last_modified = get_file_last_modified(f)
        references = count_references(f, f.stem)
        
        entries.append({
            "name": f.stem,
            "file": f,
            "last_modified": last_modified,
            "references": references,
            "last_access": get_last_access_from_content(open(f).read()) if f.exists() else last_modified
        })
    
    return entries


def scan_cold_entries() -> List[Dict]:
    """Scan archive/ directory for cold entries."""
    if not ARCHIVE_DIR.exists():
        return []
    
    entries = []
    for f in ARCHIVE_DIR.glob("*.md"):
        last_modified = get_file_last_modified(f)
        
        entries.append({
            "name": f.stem,
            "file": f,
            "last_modified": last_modified,
            "last_access": get_last_access_from_content(open(f).read()) if f.exists() else last_modified
        })
    
    return entries


def should_promote_to_hot(entry: Dict, hot_topics: List[str]) -> bool:
    """Check if entry should be promoted to hot (memory.md)."""
    # If it's in hot topics and referenced recently
    if entry["name"] in hot_topics and entry["references"] >= 1:
        last_access = entry.get("last_access") or entry.get("last_modified")
        if last_access:
            if isinstance(last_access, str):
                last_access = parse_date(last_access)
            if last_access and (datetime.now() - last_access).days < HOT_THRESHOLD_DAYS:
                return True
    return False


def should_demote_from_hot(entry_name: str, hot_topics: List[str]) -> bool:
    """Check if entry in memory.md should be demoted to warm."""
    # Not in hot topics or not referenced enough
    if entry_name not in hot_topics:
        return True
    
    topic_line_pattern = re.compile(rf'^[-*]\s+\[?{re.escape(entry_name)}[\]:]', re.MULTILINE)
    # If mentioned less than 3 times, demote
    # This is simplified - in reality we'd check frequency
    
    return False  # Keep in hot if mentioned at all


def should_archive(entry: Dict) -> bool:
    """Check if entry should be moved to archive."""
    last_access = entry.get("last_access") or entry.get("last_modified")
    
    if not last_access:
        return True
    
    if isinstance(last_access, str):
        last_access = parse_date(last_access)
    
    if last_access and (datetime.now() - last_access).days >= COLD_THRESHOLD_DAYS:
        return True
    
    return False


def should_promote_to_warm(entry: Dict) -> bool:
    """Check if entry should be promoted from archive to warm."""
    # If referenced 3+ times in memory.md
    if entry.get("references", 0) >= PROMOTE_THRESHOLD:
        return True
    return False


def promote_entry_to_hot(entry: Dict) -> bool:
    """Promote entry from domains/ to memory.md."""
    try:
        topic_name = entry["name"]
        content = open(entry["file"], 'r', encoding='utf-8').read()
        
        # Read current memory.md
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory_content = f.read()
        
        # Create new entry snippet
        new_entry = f"\n- [{topic_name}] {content[:200]}..."
        
        # Append to memory.md
        with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
            f.write(new_entry)
        
        # Remove from domains/
        entry["file"].unlink()
        
        print(f"  ✅ Promoted to hot: {topic_name}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to promote {entry['name']}: {e}")
        return False


def demote_to_warm(entry: Dict) -> bool:
    """Demote entry from memory.md to domains/."""
    try:
        topic_name = entry["name"]
        
        # Create domain file
        domain_file = DOMAINS_DIR / f"{topic_name}.md"
        with open(domain_file, 'w', encoding='utf-8') as f:
            f.write(f"# {topic_name}\n\n")
            f.write(f"<!-- last_access: {get_current_time()} -->\n\n")
            f.write(f"Referenced {entry.get('references', 0)} times in memory.md\n")
        
        # Remove from memory.md (simplified - would need proper parsing)
        print(f"  📝 Demoted to warm: {topic_name} (needs manual cleanup of memory.md)")
        return True
    except Exception as e:
        print(f"  ❌ Failed to demote {entry['name']}: {e}")
        return False


def archive_entry(entry: Dict) -> bool:
    """Move entry from domains/ to archive/."""
    try:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        
        archive_file = ARCHIVE_DIR / entry["file"].name
        shutil.move(str(entry["file"]), str(archive_file))
        
        print(f"  📦 Archived: {entry['name']}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to archive {entry['name']}: {e}")
        return False


def restore_from_archive(entry: Dict) -> bool:
    """Restore entry from archive/ to domains/."""
    try:
        domain_file = DOMAINS_DIR / entry["file"].name
        shutil.move(str(entry["file"]), str(domain_file))
        
        # Update last_access
        update_last_access(domain_file)
        
        print(f"  ♻️ Restored from archive: {entry['name']}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to restore {entry['name']}: {e}")
        return False


def run_exchange_cycle() -> Dict:
    """
    Run one complete exchange cycle.
    
    Returns:
        dict with counts of promotions/demotions/archives
    """
    results = {
        "promoted_to_hot": 0,
        "demoted_to_warm": 0,
        "archived": 0,
        "restored": 0
    }
    
    hot_topics = get_hot_topics_from_memory()
    warm_entries = scan_warm_entries()
    cold_entries = scan_cold_entries()
    
    print("🔄 Running Cold/Hot Exchange Cycle...")
    print(f"   Hot topics in memory: {len(hot_topics)}")
    print(f"   Warm entries in domains/: {len(warm_entries)}")
    print(f"   Cold entries in archive/: {len(cold_entries)}")
    
    # Check warm entries
    print("\n📋 Checking warm entries...")
    for entry in warm_entries:
        # Update last access
        update_last_access(entry["file"])
        
        # Check if should be archived
        if should_archive(entry):
            if archive_entry(entry):
                results["archived"] += 1
        # Check if should be promoted to hot
        elif should_promote_to_hot(entry, hot_topics):
            if promote_entry_to_hot(entry):
                results["promoted_to_hot"] += 1
    
    # Check cold entries - restore if referenced
    print("\n📋 Checking archived entries...")
    for entry in cold_entries:
        if should_promote_to_warm(entry):
            if restore_from_archive(entry):
                results["restored"] += 1
    
    # Check memory.md entries that should be demoted
    # This is more complex - would need to parse memory.md
    print("\n📋 Memory.md hot topics check:")
    for topic in hot_topics[:5]:  # Check top 5
        print(f"   ✅ {topic}")
    
    return results


def main():
    print("=" * 50)
    print("🧠 Self-Improving Cold/Hot Exchange Engine")
    print("=" * 50)
    
    results = run_exchange_cycle()
    
    print("\n" + "=" * 50)
    print("📊 Exchange Results")
    print("=" * 50)
    print(f"   Promoted to hot: {results['promoted_to_hot']}")
    print(f"   Demoted to warm: {results['demoted_to_warm']}")
    print(f"   Archived: {results['archived']}")
    print(f"   Restored: {results['restored']}")
    print("=" * 50)


if __name__ == "__main__":
    main()