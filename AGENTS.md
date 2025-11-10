# AGENTS.md - Development Guidelines for ONYX

**Project:** ONYX - BMAD Framework Configuration Repository  
**Last Updated:** Nov 10, 2025  
**Target Audience:** Agentic coding agents (Claude Code, OpenCode, Cline, Cursor, etc.)

---

## Build & Test Commands

This repository contains BMAD (Business Model Agile Development) framework definitions, configuration, and agent/workflow specifications. No build/test execution needed for core codebase.

- **Validate YAML configs:** `find .bmad -name "*.yaml" -exec yamllint {} +`
- **Check markdown formatting:** `find . -name "*.md" -o -name "*.mdc" | xargs prettier --check`
- **No unit tests:** This is a configuration/framework repository; test coverage applies to consuming projects

---

## Code Style Guidelines

### File Organization
- **YAML configs:** `.bmad/{module}/config.yaml` — stored as project source of truth; never modify without explicit user request
- **Agent definitions:** `.bmad/{module}/agents/{agent-name}.md` — use consistent XML schema with `<agent>`, `<activation>`, `<persona>`, `<menu>` tags
- **Workflow definitions:** `.bmad/{module}/workflows/{workflow-name}/workflow.yaml` + supporting `instructions.md`, `checklist.md`, `template.md`
- **Cursor rules:** `.cursor/rules/bmad/` — mirror BMAD structure; format as `.mdc` (Cursor markup) files with YAML frontmatter
- **Documentation:** Markdown in workflow subdirectories; READMEs mirror structure hierarchy

### Naming Conventions
- **Agent files:** kebab-case (e.g., `dev.md`, `creative-problem-solver.md`)
- **Workflow directories:** kebab-case (e.g., `dev-story`, `create-agent`)
- **Variable placeholders:** `{project-root}`, `{bmad_folder}`, `{user_name}` — use consistent curly-brace syntax
- **Menu commands:** Prefix with asterisk: `*develop-story`, `*code-review`
- **Classes/IDs in XML:** kebab-case (e.g., `id="bmad-master"`)

### Imports & Dependencies
- No external npm/package dependencies in core `.bmad/` files
- Reference files using relative paths from project root: `{project-root}/.bmad/...`
- Link workflows to instructions deterministically: `instructions: "{installed_path}/instructions.md"`
- Import agents via `@bmad/{module}/{type}/{name}` syntax in Cursor rules

### Types & Schema
- **YAML config:** Flat key-value strings; all paths use `{placeholders}` for portability
- **XML agent definitions:** Use strict `<agent>`, `<activation>`, `<step>`, `<menu>`, `<menu-handlers>` hierarchy
- **Workflow YAML:** Include `name`, `description`, `author`, config references, installed_path, instructions, validation, standalone flag
- **Frontmatter in .mdc:** Minimal YAML (description, globs, alwaysApply)

### Formatting
- **Markdown:** GFM (GitHub Flavored Markdown); headers max 3 levels unless deeply nested documentation
- **XML:** Preserve indentation; 2-space indent for nested elements
- **YAML:** 2-space indent; no tabs; sort keys alphabetically at same nesting level
- **Line length:** 100 chars target for readability; no hard requirement
- **Comments:** Use `#` for YAML/shell; `<!-- -->` for XML; `//` discouraged in prose files

### Error Handling & Validation
- **Config loading:** Always validate `{project-root}/.bmad/{module}/config.yaml` exists before referencing placeholders
- **File references:** Check file existence in activation steps before proceeding (see dev.md step 2 pattern)
- **Workflow state:** Validate `Status == Approved` before executing dev story; check context files exist
- **Error messages:** Be specific (cite full paths, step numbers); never invent missing files—ask user to generate them first
- **Graceful degradation:** If optional file missing, warn but don't halt unless marked critical

### Communication Style
- **For agents:** Succinct, checklist-driven; cite specific paths and AC (acceptance criteria) IDs
- **For users:** Professional, clear; match `{communication_language}` (default: English)
- **For docs:** Structured with examples; use numbered lists for sequences, bullet points for options
- **Menu items:** One-line descriptions; use workflow attributes (`workflow=`, `exec=`, `action=`) for execution hints

---

## Cursor Rules & Special Configurations

- **Location:** `.cursor/rules/bmad/` mirrors `.bmad/` structure exactly
- **Format:** Markdown frontmatter + `.mdc` extension (Cursor-specific markup)
- **Always Apply:** Set `alwaysApply: false` for manual reference (not auto-included)
- **References:** Use `@bmad/{module}/{type}/{name}` to include rules in context
- **Master Index:** `@bmad/index` lists all available rules; reference it when unsure what's available

**No Copilot Rules detected** (.github/copilot-instructions.md not found); follow Cursor conventions.

---

## Key Implementation Notes

1. **Story Context is authoritative:** Pin Story Context XML into memory; treat as single source of truth over any model priors
2. **Acceptance criteria driven:** Every code change must map to specific AC ID; refuse to invent when info lacking
3. **Reuse over rebuild:** Check existing interfaces/code before creating new components
4. **Tests must pass 100%:** Story is incomplete until all tests pass; halt story workflow if test failure occurs
5. **Configuration management:** Never hardcode paths; always use `{project-root}` and `{placeholders}`
6. **Run until complete:** Some workflows set `run_until_complete: true`; execute continuously without pausing for review

---

## Quick Reference

| Item | Location | Format |
|------|----------|--------|
| Project Config | `.bmad/bmm/config.yaml` | YAML (read-only) |
| Dev Agent Persona | `.bmad/bmm/agents/dev.md` | Markdown + XML |
| Workflow Orchestration | `.bmad/*/workflows/*/workflow.yaml` | YAML |
| Cursor Rules Index | `.cursor/rules/bmad/index.mdc` | Markdown (.mdc) |
| Stories (Ephemeral) | `.bmad-ephemeral/` | Markdown + XML |

---

**Next Step:** Load Story Context from referenced `.context.xml` file before implementing. Halt and ask user to generate if missing.
