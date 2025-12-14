#!/usr/bin/env python3
"""
Session Summary Extractor for Context Passport

Parses Claude conversation exports (JSON or markdown) and generates
structured summaries for appending to PASSPORT.md.

Usage:
    python session-summary.py <input_file> [--output <output_file>]
    
Examples:
    python session-summary.py conversation.json
    python session-summary.py export.md --output update.md
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def extract_from_json(filepath: Path) -> dict:
    """Extract conversation content from Claude JSON export."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    messages = []
    
    # Handle different JSON structures
    if isinstance(data, list):
        messages = data
    elif isinstance(data, dict):
        if 'messages' in data:
            messages = data['messages']
        elif 'conversation' in data:
            messages = data['conversation']
    
    # Extract text content
    content_parts = []
    for msg in messages:
        role = msg.get('role', msg.get('sender', 'unknown'))
        text = msg.get('content', msg.get('text', ''))
        if isinstance(text, list):
            text = ' '.join([t.get('text', str(t)) for t in text])
        content_parts.append(f"[{role}]: {text}")
    
    return {'raw_content': '\n\n'.join(content_parts), 'source': 'json'}


def extract_from_markdown(filepath: Path) -> dict:
    """Extract conversation content from markdown export."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return {'raw_content': content, 'source': 'markdown'}


def extract_from_pdf_text(filepath: Path) -> dict:
    """Extract text from PDF (requires pdfplumber or similar)."""
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        return {'raw_content': text, 'source': 'pdf'}
    except ImportError:
        print("Warning: pdfplumber not installed. Install with: pip install pdfplumber")
        return {'raw_content': '', 'source': 'pdf'}


def parse_content(content: str) -> dict:
    """Parse conversation content into structured summary."""
    
    # Patterns to look for
    patterns = {
        'decisions': [
            r'(?:decided|chose|going with|will use|picked|selected)[\s:]+(.+?)(?:\.|$)',
            r'(?:decision|choice)[\s:]+(.+?)(?:\.|$)',
        ],
        'code_changes': [
            r'(?:created|built|added|implemented|fixed|updated|wrote)[\s:]+(.+?)(?:\.|$)',
            r'(?:file|script|component|function)[\s:]+(\S+)',
        ],
        'blockers': [
            r'(?:blocked by|stuck on|need to|waiting for|cant|cannot)[\s:]+(.+?)(?:\.|$)',
            r'(?:blocker|issue|problem)[\s:]+(.+?)(?:\.|$)',
        ],
        'next_actions': [
            r'(?:next|todo|will do|should|going to)[\s:]+(.+?)(?:\.|$)',
            r'(?:action item|next step)[\s:]+(.+?)(?:\.|$)',
        ],
    }
    
    results = {key: set() for key in patterns}
    
    # Search for patterns (case insensitive)
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 5:  # Filter out too-short matches
                    results[category].add(match.strip()[:100])  # Limit length
    
    return {k: list(v)[:5] for k, v in results.items()}  # Max 5 per category


def generate_summary(parsed: dict, topic: Optional[str] = None) -> str:
    """Generate markdown summary for Context Stack."""
    
    date = datetime.now().strftime("%Y-%m-%d")
    topic = topic or "Session Update"
    
    lines = [f"### {date} - {topic}", ""]
    
    if parsed.get('decisions'):
        lines.append("**Decisions:**")
        for item in parsed['decisions']:
            lines.append(f"- {item}")
        lines.append("")
    
    if parsed.get('code_changes'):
        lines.append("**Changes:**")
        for item in parsed['code_changes']:
            lines.append(f"- {item}")
        lines.append("")
    
    if parsed.get('blockers'):
        lines.append("**Blockers:**")
        for item in parsed['blockers']:
            lines.append(f"- {item}")
        lines.append("")
    
    if parsed.get('next_actions'):
        lines.append("**Next:**")
        for item in parsed['next_actions']:
            lines.append(f"- {item}")
        lines.append("")
    
    # If nothing was extracted, provide placeholder
    if len(lines) == 2:
        lines.extend([
            "**Summary:** [Manual entry needed - auto-extraction found no patterns]",
            "",
            "**Next:** [Add next action]",
            ""
        ])
    
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = None
    topic = None
    
    # Parse arguments
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--output' and i + 1 < len(args):
            output_path = Path(args[i + 1])
            i += 2
        elif args[i] == '--topic' and i + 1 < len(args):
            topic = args[i + 1]
            i += 2
        else:
            i += 1
    
    # Determine file type and extract
    suffix = input_path.suffix.lower()
    if suffix == '.json':
        extracted = extract_from_json(input_path)
    elif suffix in ['.md', '.markdown', '.txt']:
        extracted = extract_from_markdown(input_path)
    elif suffix == '.pdf':
        extracted = extract_from_pdf_text(input_path)
    else:
        print(f"Unsupported file type: {suffix}")
        sys.exit(1)
    
    # Parse and generate summary
    parsed = parse_content(extracted['raw_content'])
    summary = generate_summary(parsed, topic)
    
    # Output
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"Summary written to: {output_path}")
    else:
        print("\n" + "=" * 50)
        print("CONTEXT STACK UPDATE")
        print("=" * 50)
        print(summary)
        print("=" * 50)
        print("\nCopy the above to your PASSPORT.md Context Stack section.")


if __name__ == '__main__':
    main()
