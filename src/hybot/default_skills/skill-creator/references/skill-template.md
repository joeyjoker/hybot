# SKILL.md Template

Copy and adapt this template when creating a new skill.

```markdown
---
name: your-skill-name
description: "Brief description of what this skill does (max 1024 chars)."
license: "MIT"
compatibility: "Any requirements or constraints (max 500 chars)"
allowed-tools:
  - coding
  - python
metadata:
  version: "1.0.0"
  author: "Author Name"
  tags:
    - tag1
    - tag2
---

# Skill Title

## Purpose
Explain what this skill enables the agent to do.

## When to Use
Describe the scenarios where this skill should be activated.

## Instructions

### Step 1: ...
Detailed guidance...

### Step 2: ...
More guidance...

## Examples

### Example 1: ...
Show a concrete example of usage.

## Notes
Any additional information the agent needs.
```

## Quick Reference: Validation Rules

| Field | Required | Type | Constraints |
|-------|----------|------|-------------|
| `name` | Yes | string | lowercase, a-z/0-9/hyphens only, max 64 chars, no leading/trailing/consecutive hyphens, must match directory name |
| `description` | Yes | string | non-empty, max 1024 chars |
| `license` | No | string | - |
| `compatibility` | No | string | max 500 chars |
| `allowed-tools` | No | list[string] | - |
| `metadata` | No | dict | may contain `version`, `author`, `tags` etc. |

No other fields are allowed in frontmatter.
