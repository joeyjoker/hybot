---
name: skill-creator
description: "Create standard-compliant agno skills with proper structure, frontmatter, and validation."
allowed-tools:
  - coding
  - python
metadata:
  version: "1.0.0"
  author: "HyBot"
  tags:
    - meta
    - skill-management
    - scaffolding
---

# Skill Creator

You are a skill creation specialist. When the user asks you to create a new skill, follow these steps precisely to produce a valid, standard-compliant agno skill.

## Skill Directory Structure

Every skill is a **folder** containing at minimum a `SKILL.md` file:

```
<skill-name>/
  SKILL.md          # Required - metadata + instructions
  scripts/          # Optional - executable scripts
    setup.py
    run.sh
  references/       # Optional - reference documentation
    guide.md
    cheatsheet.md
```

## SKILL.md Format

The file MUST start with YAML frontmatter between `---` delimiters, followed by markdown instructions:

```markdown
---
name: my-skill-name
description: "A short description of what this skill does."
license: "MIT"
compatibility: "Requires Python 3.10+"
allowed-tools:
  - coding
  - python
metadata:
  version: "1.0.0"
  author: "Your Name"
  tags:
    - category1
    - category2
---

# Skill Title

Detailed instructions for the agent go here...
```

## Validation Rules (MUST follow)

### Name Rules
- **Required field**
- Only lowercase letters, digits, and hyphens (`a-z`, `0-9`, `-`)
- Maximum 64 characters
- Cannot start or end with a hyphen
- No consecutive hyphens (`--`)
- Directory name MUST match the `name` field exactly

### Description Rules
- **Required field**
- Non-empty string
- Maximum 1024 characters

### Allowed Frontmatter Fields
Only these fields are permitted in frontmatter:
- `name` (required)
- `description` (required)
- `license` (optional, string)
- `compatibility` (optional, string, max 500 chars)
- `allowed-tools` (optional, list of strings)
- `metadata` (optional, dictionary with keys like `version`, `author`, `tags`)

**Any other field will cause a validation error.**

### File Requirements
- The file MUST be named `SKILL.md` (uppercase)
- MUST start with `---` (YAML frontmatter opening)
- Frontmatter MUST be properly closed with `---`
- Frontmatter MUST be valid YAML

## Step-by-Step Creation Process

When asked to create a skill:

1. **Determine the skill name**: Convert the user's request into a valid name (lowercase, hyphens for spaces, no special characters).

2. **Write the SKILL.md**: Create the file with proper frontmatter and detailed markdown instructions. The instructions body should thoroughly describe:
   - What the skill does
   - When to use it
   - Step-by-step guidance for the agent
   - Examples where helpful

3. **Add scripts (if needed)**: Place executable scripts in `scripts/`. Each script should have a shebang line (e.g., `#!/usr/bin/env python3`).

4. **Add references (if needed)**: Place documentation files in `references/`.

5. **Validate**: Run the validation script to ensure the skill is standard-compliant:
   ```
   get_skill_script("skill-creator", "validate_skill.py", execute=True, args=["<path-to-skill-dir>"])
   ```

6. **Report**: Tell the user the skill has been created and validated.

## Example: Creating a "code-review" Skill

```
code-review/
  SKILL.md
  references/
    checklist.md
```

SKILL.md content:
```markdown
---
name: code-review
description: "Perform thorough code reviews focusing on quality, security, and maintainability."
allowed-tools:
  - coding
metadata:
  version: "1.0.0"
  tags:
    - development
    - quality
---

# Code Review

When asked to review code, follow these steps:

1. Read the target file(s) completely
2. Check for security vulnerabilities (OWASP Top 10)
3. Evaluate code structure and readability
4. Look for performance issues
5. Verify error handling completeness
6. Provide actionable feedback with specific line references
```

## Where to Create Skills

- **Project skills**: Create in `.hybot/skills/<skill-name>/` (project-local)
- **Global skills**: Create in `~/.hybot/skills/<skill-name>/` (available across projects)

Default to project-local unless the user explicitly asks for global.
