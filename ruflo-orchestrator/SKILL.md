---
name: ruflo-orchestrator
description: |
  Orchestrate multi-agent AI swarms using Ruflo's MCP tools (mcp__ruflo__*). Use when the user wants to coordinate multiple AI agents, run agent swarms, do consensus code reviews, perform security audits with AIDefence, manage agent memory/patterns, or build workflow pipelines. Trigger on: "ruflo", "swarm", "hive mind", "multi-agent", "agent team", "coordinate agents", "consensus review", "workflow pipeline", "spin up agents", "spawn agents", "security scan", "prompt injection", "orchestrate", or parallelizing work across specialized agents (architect, coder, tester, reviewer). Also trigger for agent memory, learned patterns, or storing/retrieving knowledge across sessions. Do NOT trigger for standard single-agent tasks like normal code review, writing tests, debugging, refactoring, or deployment — only when multi-agent coordination or Ruflo-specific features are needed.
---

# Ruflo Orchestrator

Ruflo is a multi-agent AI orchestration framework available as an MCP server. It provides 60+ specialized agents, swarm coordination, security scanning, persistent memory, and workflow automation — all accessible through `mcp__ruflo__*` tools.

This skill teaches you when and how to use those tools effectively.

## Core Concepts

Ruflo organizes work through a hierarchy:

- **Swarm**: The runtime environment where agents operate. You initialize one with a topology (how agents communicate) and it manages the lifecycle.
- **Agents**: Specialized workers (coder, tester, reviewer, architect, security, etc.) that you spawn into the swarm. Each has a type and can be assigned tasks.
- **Tasks**: Units of work created and assigned to agents. Tasks have types (feature, bugfix, research, refactor), priorities, and status tracking.
- **Memory**: Persistent vector-backed storage that survives across sessions. Agents can store learnings, retrieve patterns, and search semantically.
- **Workflows**: Reusable multi-step pipelines that chain tasks, conditions, and parallel stages together.

## Choosing the Right Workflow

Not every request needs a full swarm. Match the complexity of Ruflo's tools to the task:

| User wants... | What to use | Why |
|---|---|---|
| Quick security check on some text | `aidefence_scan` or `aidefence_is_safe` alone | No swarm needed, single tool call |
| Store/retrieve a piece of knowledge | `memory_store` / `memory_retrieve` alone | Direct key-value operation |
| Check system health | `system_status` or `system_health` alone | Diagnostic, no agents needed |
| Multi-agent feature development | Full swarm workflow (see below) | Multiple agents coordinating |
| Code review with multiple perspectives | Review workflow (see below) | Needs consensus mechanism |
| Comprehensive security audit | Security workflow (see below) | Multiple scan types + analysis |
| Recurring multi-step pipeline | Workflow creation (see below) | Reusable automation |

## Workflow: Multi-Agent Task Execution

Use this when the user wants multiple specialized agents working together on a feature, refactor, or complex task.

### Step 1: Initialize the swarm

```
mcp__ruflo__swarm_init({
  topology: "hierarchical",  // best for coordinated work; use "mesh" for peer-to-peer
  maxAgents: 6               // 4-8 is the sweet spot; more agents = more coordination overhead
})
```

Topology guide:
- **hierarchical** — one coordinator routes work to specialists. Best default for most tasks.
- **mesh** — all agents communicate directly. Good for brainstorming or research where every perspective matters.
- **star** — central hub with spokes. Good when one agent aggregates results from many.
- **ring** — sequential pipeline. Good for staged workflows (write → review → test).

### Step 2: Spawn the right agents

Pick agent types based on the task. Here are all valid agent types:

**Core agents:**

| Agent Type | Purpose |
|---|---|
| `coordinator` | Orchestrates other agents, manages workflow |
| `coder` | Writes and implements code |
| `tester` | Writes and runs tests |
| `reviewer` | Reviews code for quality and correctness |
| `architect` | Designs systems and architecture |
| `researcher` | Analyzes requirements and researches solutions |

**Specialized agents:**

| Agent Type | Purpose |
|---|---|
| `security-architect` | Security design and threat modeling |
| `security-auditor` | Security auditing and vulnerability scanning |
| `memory-specialist` | Manages agent memory and knowledge |
| `performance-engineer` | Performance optimization and profiling |

**Swarm coordination agents** (use these as the coordinator in larger swarms):

| Agent Type | Purpose |
|---|---|
| `hierarchical-coordinator` | Manages hierarchical swarm topology |
| `mesh-coordinator` | Manages mesh swarm topology |
| `adaptive-coordinator` | Dynamically adjusts coordination strategy |

**Consensus agents** (use these when you need specific consensus algorithms):

| Agent Type | Purpose |
|---|---|
| `byzantine-coordinator` | Byzantine fault-tolerant consensus |
| `raft-manager` | Raft consensus algorithm |
| `gossip-coordinator` | Gossip protocol coordination |

Common combinations for tasks:

| Task | Agents to spawn |
|---|---|
| Build a feature | `architect`, `coder`, `tester` |
| Refactor code | `coder`, `reviewer`, `performance-engineer` |
| Full feature with security | `architect`, `coder`, `tester`, `security-architect`, `reviewer` |
| Research & analysis | `researcher`, `architect` |
| Code review with consensus | `reviewer`, `security-architect`, `architect` |

```
mcp__ruflo__agent_spawn({
  agentType: "coder",
  model: "sonnet",        // "haiku" for simple tasks, "sonnet" balanced, "opus" for complex reasoning
  task: "implement JWT authentication"  // helps with intelligent model routing
})
```

Spawn each agent you need. Save the returned agent IDs — you'll need them for task assignment.

### Step 3: Create and assign tasks

```
mcp__ruflo__task_create({
  type: "feature",           // feature | bugfix | research | refactor
  description: "Implement JWT-based authentication with refresh tokens",
  priority: "high",          // low | normal | high | critical
  assignTo: ["agent-id-1", "agent-id-2"]
})
```

For complex work, break it into subtasks and assign each to the most appropriate agent.

### Step 4: Monitor progress

```
mcp__ruflo__task_status({ taskId: "task-id" })
mcp__ruflo__swarm_health({ swarmId: "swarm-id" })
mcp__ruflo__agent_status({ agentId: "agent-id" })
```

Check periodically. If an agent is unhealthy, check `agent_health` and consider terminating and respawning it.

### Step 5: Collect results and clean up

```
mcp__ruflo__task_complete({ taskId: "task-id", result: { /* output data */ } })
mcp__ruflo__swarm_shutdown({ swarmId: "swarm-id", graceful: true })
```

Always use graceful shutdown so agents can finish in-flight work.

## Workflow: Multi-Agent Code Review with Consensus

Use when the user wants thorough code review from multiple perspectives.

### Steps

1. **Init swarm** with mesh topology (every reviewer sees every other's perspective):
   ```
   mcp__ruflo__swarm_init({ topology: "mesh", maxAgents: 4 })
   ```

2. **Spawn reviewers** — typically a `reviewer`, `security-architect`, and `architect`:
   ```
   mcp__ruflo__agent_spawn({ agentType: "reviewer", model: "sonnet" })
   mcp__ruflo__agent_spawn({ agentType: "security-architect", model: "sonnet" })
   mcp__ruflo__agent_spawn({ agentType: "architect", model: "sonnet" })
   ```

3. **Set up consensus** — choose the algorithm based on how rigorous the review needs to be:
   ```
   mcp__ruflo__coordination_consensus({
     algorithm: "weighted",    // or "majority", "byzantine" for critical code
     threshold: 0.7
   })
   ```
   - **majority** — simple vote, good for most reviews
   - **weighted** — gives more weight to domain experts (e.g., security agent's opinion on auth code)
   - **byzantine** — fault-tolerant, use for critical/production code where you want high confidence

4. **Orchestrate the review**:
   ```
   mcp__ruflo__coordination_orchestrate({
     task: "Review authentication module for security, architecture, and code quality",
     agents: ["reviewer-id", "security-id", "architect-id"],
     strategy: "parallel"    // all review simultaneously
   })
   ```

5. **Shut down** when done.

## Workflow: Security Audit

Use when the user wants to scan code or inputs for vulnerabilities.

### Quick scan (single input)

For checking whether a specific piece of text is safe (e.g., user input validation):

```
mcp__ruflo__aidefence_is_safe({ input: "the text to check" })
```

Returns a simple boolean. Use this for fast validation gates.

### Detailed scan

For understanding what threats exist and getting recommendations:

```
mcp__ruflo__aidefence_scan({
  input: "the text or code to scan",
  quick: false                // full analysis
})
```

### Deep analysis with pattern matching

For the most thorough analysis — compares against known threat patterns:

```
mcp__ruflo__aidefence_analyze({
  input: "the text or code to analyze",
  searchSimilar: true,        // find similar known threats
  k: 5                        // number of similar patterns to retrieve
})
```

### Recording results for learning

After a scan, record whether the detection was accurate so the system improves over time:

```
mcp__ruflo__aidefence_learn({
  input: "the original input",
  wasAccurate: true,
  verdict: "correctly identified SQL injection attempt"
})
```

## Workflow: Hive Mind (Advanced Swarm)

The hive mind is a more structured swarm with a queen-worker hierarchy. Use it for large, complex tasks that need strong coordination.

1. **Initialize** with a queen:
   ```
   mcp__ruflo__hive-mind_init({ topology: "hierarchical" })
   ```

2. **Spawn workers** directly into the hive:
   ```
   mcp__ruflo__hive-mind_spawn({
     count: 4,
     role: "worker",          // worker | specialist | scout
     agentType: "coder"
   })
   ```

3. **Broadcast** instructions to all workers:
   ```
   mcp__ruflo__hive-mind_broadcast({ message: "Focus on error handling in the auth module" })
   ```

4. **Check status**:
   ```
   mcp__ruflo__hive-mind_status({ verbose: true })
   ```

5. **Shut down** when complete:
   ```
   mcp__ruflo__hive-mind_shutdown({})
   ```

## Workflow: Persistent Memory

Ruflo's memory system uses vector embeddings for semantic search. Use it to store and retrieve knowledge across sessions.

### Store knowledge

```
mcp__ruflo__memory_store({
  key: "auth-pattern-jwt",
  value: "JWT auth implementation: use RS256, rotate keys every 90 days, store refresh tokens in httpOnly cookies",
  namespace: "patterns",
  tags: ["auth", "jwt", "security"]
})
```

### Retrieve by key

```
mcp__ruflo__memory_retrieve({ key: "auth-pattern-jwt", namespace: "patterns" })
```

### Search semantically

```
mcp__ruflo__memory_search({ query: "how to handle authentication tokens", limit: 5 })
```

### Check what's stored

```
mcp__ruflo__memory_list({ namespace: "patterns", limit: 20 })
mcp__ruflo__memory_stats({})
```

## Workflow: Reusable Pipelines

For recurring multi-step processes, create a workflow once and run it repeatedly.

### Create a workflow

```
mcp__ruflo__workflow_create({
  name: "feature-pipeline",
  description: "Standard feature development pipeline",
  steps: [
    { name: "design", type: "task", config: { agentType: "architect" } },
    { name: "implement", type: "task", config: { agentType: "coder" } },
    { name: "test-and-review", type: "parallel", config: {
      tasks: [
        { agentType: "tester" },
        { agentType: "reviewer" }
      ]
    }},
    { name: "security-check", type: "task", config: { agentType: "security" } }
  ]
})
```

### Run it

```
mcp__ruflo__workflow_run({
  template: "feature-pipeline",
  task: "Add OAuth2 support",
  options: { parallel: true, maxAgents: 6 }
})
```

### Monitor and control

```
mcp__ruflo__workflow_status({ workflowId: "wf-id", verbose: true })
mcp__ruflo__workflow_pause({ workflowId: "wf-id" })     // pause if needed
mcp__ruflo__workflow_resume({ workflowId: "wf-id" })    // resume
```

## Performance Monitoring

Use these tools to understand and optimize Ruflo's performance:

```
// Quick health check
mcp__ruflo__system_status({})

// Detailed performance metrics
mcp__ruflo__performance_metrics({ metric: "all", timeRange: "1h" })

// Find bottlenecks
mcp__ruflo__performance_bottleneck({ deep: true })

// Run benchmarks
mcp__ruflo__performance_benchmark({ suite: "all", iterations: 3 })

// Generate a report
mcp__ruflo__performance_report({ format: "detailed", timeRange: "24h" })

// Apply optimizations
mcp__ruflo__performance_optimize({ target: "all" })
```

## Hooks & Intelligence

Ruflo has a hooks system that can intercept actions for pre-flight checks and post-action learning:

```
// Check risk before running a command
mcp__ruflo__hooks_pre-command({ command: "rm -rf ./dist" })

// Get suggestions before editing a file
mcp__ruflo__hooks_pre-edit({ filePath: "./src/auth.ts", operation: "refactor" })

// Record outcome for learning
mcp__ruflo__hooks_post-edit({ filePath: "./src/auth.ts", success: true })

// Route to optimal model/agent
mcp__ruflo__hooks_route({ task: "add error handling to auth module" })
```

## GitHub Integration

Ruflo can interact with GitHub repositories:

```
// Analyze a repo
mcp__ruflo__github_repo_analyze({ owner: "myorg", repo: "myapp", deep: true })

// Manage PRs
mcp__ruflo__github_pr_manage({
  action: "create",
  owner: "myorg", repo: "myapp",
  branch: "feature/auth", baseBranch: "main",
  title: "Add JWT authentication",
  body: "Implements JWT-based auth with refresh tokens"
})

// Track issues
mcp__ruflo__github_issue_track({
  action: "create",
  owner: "myorg", repo: "myapp",
  title: "Security audit findings",
  labels: ["security", "audit"]
})
```

## Quick Reference: When to Use What

| Trigger phrase | Tools to use |
|---|---|
| "use multiple agents to..." | swarm_init → agent_spawn → task_create → task_assign |
| "review this with consensus" | swarm_init (mesh) → agent_spawn (reviewers) → coordination_consensus → coordination_orchestrate |
| "is this input safe?" | aidefence_is_safe |
| "security audit" | aidefence_scan + aidefence_analyze |
| "remember this" / "store this pattern" | memory_store |
| "what did we learn about...?" | memory_search or memory_retrieve |
| "create a pipeline for..." | workflow_create → workflow_run |
| "how's the system doing?" | system_status or performance_metrics |
| "optimize performance" | performance_bottleneck → performance_optimize |
| "spawn a hive" | hive-mind_init → hive-mind_spawn |
| "analyze this repo" | github_repo_analyze |
