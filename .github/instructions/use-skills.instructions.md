# Agent Skills Instructions

This project maintains a collection of agent skills in the `.claude/skills` directory.
These skills adhere to the [Agent Skills Specification](https://agentskills.io/specification).

## Agent Workflow (CRITICAL)

Before executing ANY complex task (especially releases, refactoring, or testing), you MUST follow this workflow:

1.  **Check for Skills**: 
    - Scan the `.claude/skills` directory to find potential skills.
    - **Performance Optimization**: To avoid context overload, **ONLY read the Frontmatter** (the YAML block at the top between `---` lines) of each `SKILL.md` file first.
    - Example Frontmatter:
      ```yaml
      ---
      name: skill-name
      description: A description of what this skill does and when to use it.
      ---
      ```

2.  **Match Skill**: 
    - Compare the `description` in the Frontmatter with the user's current request.
    - **ONLY** if the skill is a strong match, proceed to read the full content of that specific `SKILL.md`.

3.  **Execute Skill**: 
    - If a matching skill content is loaded, you **MUST** follow its defined workflow step-by-step strictly.
    - The skill definition supersedes general instructions for that specific task.

4.  **Fallback**:
    - If no relevant skill is found after checking Frontmatter, proceed with your general knowledge and other guidelines.
