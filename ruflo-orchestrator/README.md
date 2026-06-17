# Ruflo Orchestrator

Orchestrate multi-agent AI workflows using
[Ruflo](https://github.com/ruvnet/ruflo).

## What it does

This skill teaches an agent how to effectively use Ruflo's 100+ MCP tools to:

- **Coordinate agent swarms** — initialize swarms with the right topology (hierarchical, mesh, star, ring) and spawn specialized agents
- **Run consensus code reviews** — multiple reviewer agents evaluate code independently, then reach consensus
- **Perform security audits** — scan inputs for prompt injection, PII, and other threats using AIDefence
- **Manage persistent memory** — store and retrieve learned patterns across sessions
- **Build workflow pipelines** — create reusable multi-step automation chains
- **Monitor performance** — profile, benchmark, and optimize agent workloads

It covers all 16 Ruflo agent types across 4 categories (core, specialized, swarm coordination, consensus) and includes decision tables for choosing the right workflow complexity.

## Installation

Claude Code:

```bash
npx skills add YiftachCohen/skills --skill ruflo-orchestrator
```

Codex can use the same `ruflo-orchestrator/SKILL.md` directory when it is
linked or copied into the Codex skills folder.

## Prerequisites

Ruflo must be configured as an MCP server in the agent runtime. The skill
expects `mcp__ruflo__*` tools to be available.

## When it triggers

The skill activates when you mention multi-agent coordination, swarms,
consensus reviews, security scanning, agent memory, or Ruflo directly. It does
not trigger for standard single-agent tasks like normal code review, debugging,
or deployment.
