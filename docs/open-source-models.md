# Open Source Models for Ralph Workflow

This guide covers using local open source models as alternatives to Claude Code for the Ralph Wiggum agentic development workflow.

## Prerequisites

- **Hardware**: Apple Silicon Mac with 16GB+ RAM (48GB recommended for larger models)
- **Software**: Ollama v0.14.0+ (for Anthropic API compatibility)
- **Optional**: Claude Code as cloud fallback

## Quick Start

```bash
# 1. Setup Ollama and models
./scripts/setup-ollama.sh

# 2. Run Ralph with local model
./templates/loop.sh --local minimax-m2.1

# 3. Or use Claude Code directly with Ollama
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:11434
claude --model minimax-m2.1
```

## Ollama Anthropic API Compatibility

Ollama v0.14.0+ supports the Anthropic Messages API natively. This means **Claude Code works directly with open source models** by setting two environment variables:

```bash
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:11434
claude --model <model-name>
```

The `loop.sh` script handles this automatically with the `--local` flag.

## Recommended Models

### Tier 1: Best for 48GB M4 Mac

| Model | Memory | Speed | Best For | Ollama Command |
|-------|--------|-------|----------|----------------|
| **MiniMax M2.1** | ~9GB | 50-80 t/s | Agentic tasks, tool calling | `ollama pull minimax-m2.1` |
| **Qwen2.5 Coder 32B** | ~20GB | 20-30 t/s | Max coding power | `ollama pull qwen2.5-coder:32b` |
| **Qwen2.5 Coder 7B** | ~4GB | 80+ t/s | Fast iterations | `ollama pull qwen2.5-coder:7b` |

### Why These Models?

#### MiniMax M2.1 (Recommended for Agentic Tasks)
- Only 10B activated parameters (despite 229B total MoE architecture)
- 49.4% on Multi-SWE-Bench (competitive with Claude 3.5 Sonnet)
- Advanced "Interleaved Thinking" optimized for tool calling
- Works well with Claude Code, Cline, and other agentic frameworks
- Best balance of capability and resource usage

#### Qwen2.5 Coder 32B (Maximum Coding Capability)
- Competitive with GPT-4o on coding benchmarks
- Best open-source performer on code generation tasks
- Fits comfortably in 48GB at Q4_K_M quantization
- Excellent for complex refactoring and architecture decisions

#### Qwen2.5 Coder 7B (Speed Priority)
- Nearly matches GPT-4o performance on many benchmarks
- Only 4GB memory footprint
- 80+ tokens/second on M4
- Ideal for rapid iteration and simple tasks

### Tier 2: Additional Options

| Model | Memory | Use Case | Ollama Command |
|-------|--------|----------|----------------|
| GPT-OSS 20B | ~12GB | Complex reasoning | `ollama pull gpt-oss:20b` |
| Arcee Agent 7B | ~5GB | Specialized tool calling | `ollama pull arcee-agent:7b` |
| DeepSeek Coder V2 | ~15GB | Multi-language (300+) | `ollama pull deepseek-coder-v2` |
| Codestral 22B | ~13GB | Code review, bug fixing | `ollama pull codestral:22b` |

### Models Too Large for Local

| Model | Why Skip |
|-------|----------|
| Kimi K2 | 1T params, needs 250GB+ VRAM |
| GLM 4.7 full | 355B params, needs 200GB+ VRAM |

## Usage with Ralph Loop

### Basic Usage

```bash
# Cloud (Claude Code default)
./templates/loop.sh plan 5

# Local with MiniMax M2.1
./templates/loop.sh plan 5 --local minimax-m2.1

# Local with Qwen 7B (faster)
./templates/loop.sh --local qwen2.5-coder:7b

# Build mode with local model
./templates/loop.sh 20 --local minimax-m2.1
```

### Argument Order

The `--local` flag can appear anywhere in the argument list:

```bash
./templates/loop.sh --local minimax-m2.1           # Build mode
./templates/loop.sh plan --local minimax-m2.1      # Plan mode
./templates/loop.sh plan 5 --local minimax-m2.1    # Plan mode, 5 iterations
./templates/loop.sh 20 --local qwen2.5-coder:7b    # Build mode, 20 iterations
```

## Expected Performance

### On MacBook Pro M4 48GB

| Model | Memory Used | Remaining | Token Speed | Context Window |
|-------|-------------|-----------|-------------|----------------|
| MiniMax M2.1 | ~9GB | ~39GB | 50-80 t/s | 204K tokens |
| Qwen 7B | ~4GB | ~44GB | 80+ t/s | 32K tokens |
| Qwen 32B | ~20GB | ~28GB | 20-30 t/s | 32K tokens |

### Comparison vs Claude Code

| Aspect | Local Models | Claude Code |
|--------|--------------|-------------|
| Latency | Lower (no network) | Higher (API calls) |
| Cost | Free after setup | Per-token pricing |
| Capability | Good for most tasks | Best for complex reasoning |
| Context | Limited (32K-204K) | Large (200K+) |
| Tool calling | Varies by model | Excellent |

## Evaluation Framework

Compare models using the evaluation script:

```bash
./scripts/evaluate-models.sh plan
```

This runs each configured model through a single planning iteration and logs:
- Task completion status
- Execution time
- Output for manual quality review

Results are saved to `results/<model>-<timestamp>.log`.

### Evaluation Criteria

1. **Task Completion**: Did the model finish the requested task?
2. **Plan/Code Quality**: Manual review of output coherence and correctness
3. **Execution Time**: Total wall-clock time for the iteration
4. **Error Handling**: How well did it recover from issues?
5. **Tool Usage**: Did it use tools appropriately?

## Recommended Workflow

### Daily Development

1. **Start with local models** for quick iterations:
   ```bash
   ./templates/loop.sh --local qwen2.5-coder:7b
   ```

2. **Fall back to Claude Code** for:
   - Complex architectural decisions
   - Debugging difficult issues
   - Tasks requiring extensive reasoning

### Model Selection Guide

| Task Type | Recommended Model |
|-----------|-------------------|
| Quick file edits | Qwen 7B (speed) |
| Planning | MiniMax M2.1 (tool calling) |
| Complex refactoring | Qwen 32B or Claude Code |
| Debugging | Claude Code (complex reasoning) |
| Code review | Local models work well |

## Troubleshooting

### Ollama Server Not Running

```
Error: Ollama server not responding at localhost:11434
```

**Solution**: Start Ollama server:
```bash
ollama serve
```

### Model Not Found

```
Error: model 'minimax-m2.1' not found
```

**Solution**: Pull the model first:
```bash
ollama pull minimax-m2.1
```

### Out of Memory

If you see memory errors or severe slowdown:
1. Try a smaller model (e.g., Qwen 7B instead of 32B)
2. Close other memory-intensive applications
3. Consider using Claude Code for this task

### Slow Token Generation

Expected speeds on M4:
- Qwen 7B: 80+ t/s
- MiniMax M2.1: 50-80 t/s
- Qwen 32B: 20-30 t/s

If significantly slower:
1. Check Activity Monitor for memory pressure
2. Ensure no other heavy processes running
3. Restart Ollama: `ollama stop && ollama serve`

### Tool Calling Issues

Some models handle tool calling better than others:
- **Best**: MiniMax M2.1 (designed for this)
- **Good**: Qwen 2.5 Coder series
- **Variable**: Other models

If a model struggles with tools, try MiniMax M2.1 or fall back to Claude Code.

## Version Requirements

- **Ollama**: v0.14.0+ (required for Anthropic API compatibility)
- **Claude Code**: Latest version
- **macOS**: 13.0+ for optimal Apple Silicon support

Check versions:
```bash
ollama --version
claude --version
```

## See Also

- [Ralph Wiggum Methodology](ralph-wiggum-methodology.md) - Core workflow concepts
- [Anthropic Best Practices](anthropic-best-practices.md) - Official guidance
- [Oversight and Control](oversight-and-control.md) - Sandbox setup
