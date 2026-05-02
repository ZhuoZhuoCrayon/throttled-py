# Agent Skills Instructions

This project maintains agent skills in the `.agents/skills` directory.
These skills follow the [Agent Skills Specification](https://agentskills.io/specification).

## Agent Workflow (CRITICAL)

Before executing any complex task, especially releases, refactoring, or testing, follow this workflow:

1. **Check for Skills**
   - Scan `.agents/skills` for available project skills.
   - To avoid context overload, first read only the frontmatter at the top of each `SKILL.md` file.
   - Frontmatter is the YAML block between the opening and closing `---` lines.

2. **Match Skill**
   - Compare each skill `description` with the current request.
   - Only read the full body of a skill when the description is a strong match.

3. **Execute Skill**
   - If a matching skill is loaded, follow its workflow step by step.
   - The matching skill supersedes general instructions for that specific task.

4. **Fallback**
   - If no relevant skill exists, continue with `AGENTS.md`, `CONTRIBUTING.md`, and task-specific project guidance.
