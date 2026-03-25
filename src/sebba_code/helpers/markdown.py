"""Provides markdown manipulation utilities for section appending and replacement."""

def append_to_section(content: str, header: str, line: str) -> str:
    """Append a line to a markdown section identified by header. Skips duplicates."""
    # Deduplicate: if the exact line already exists in the content, skip
    if line.strip() in [l.strip() for l in content.split("\n")]:
        return content

    lines = content.split("\n")
    insert_at = None
    in_section = False

    for i, l in enumerate(lines):
        if l.strip() == header:
            in_section = True
            continue
        if in_section:
            if l.startswith("##") and l.strip() != header:
                insert_at = i
                break
            insert_at = i + 1

    if insert_at is None:
        # Section not found — append at end
        lines.append(f"\n{header}")
        lines.append(line)
    else:
        lines.insert(insert_at, line)

    return "\n".join(lines)


def replace_section(content: str, header: str, new_body: str) -> str:
    """Replace the body of a markdown section."""
    lines = content.split("\n")
    start = None
    end = None

    for i, l in enumerate(lines):
        if l.strip() == header:
            start = i + 1
            continue
        if start is not None and end is None and l.startswith("##"):
            end = i
            break

    if start is None:
        # Section not found — append
        return content + f"\n\n{header}\n{new_body}"

    if end is None:
        end = len(lines)

    result = lines[:start] + [new_body] + lines[end:]
    return "\n".join(result)


def summarise_file(filepath: str, content: str) -> str:
    """For large files, extract key declarations only."""
    lines = content.split("\n")
    important = []
    keywords = (
        "export",
        "class ",
        "interface ",
        "type ",
        "function ",
        "const ",
        "async function",
        "describe(",
        "it(",
        "def ",
        "async def ",
    )
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(kw) for kw in keywords):
            important.append(f"L{i + 1}: {stripped}")

    return f"// {filepath} ({len(lines)} lines)\n" + "\n".join(important[:30])
