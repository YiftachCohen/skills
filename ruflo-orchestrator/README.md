# Ruflo Orchestrator Skill

A Claude Code skill for orchestrating multi-agent AI swarms using [Ruflo](https://github.com/ruvnet/ruflo).

## What it does

This skill teaches Claude how to effectively use Ruflo's 100+ MCP tools to:

- **Coordinate agent swarms** — initialize swarms with the right topology (hierarchical, mesh, star, ring) and spawn specialized agents
- **Run consensus code reviews** — multiple reviewer agents evaluate code independently, then reach consensus
- **Perform security audits** — scan inputs for prompt injection, PII, and other threats using AIDefence
- **Manage persistent memory** — store and retrieve learned patterns across sessions
- **Build workflow pipelines** — create reusable multi-step automation chains
- **Monitor performance** — profile, benchmark, and optimize agent workloads

It covers all 16 Ruflo agent types across 4 categories (core, specialized, swarm coordination, consensus) and includes decision tables for choosing the right workflow complexity.

## Installation

```bash
npx skills add YiftachCohen/skills
```

## Prerequisites

Ruflo must be configured as an MCP server in your Claude Code setup. The skill expects `mcp__ruflo__*` tools to be available.

## When it triggers

The skill activates when you mention multi-agent coordination, swarms, consensus reviews, security scanning, agent memory, or Ruflo directly. It does **not** trigger for standard single-agent tasks like normal code review, debugging, or deployment.
