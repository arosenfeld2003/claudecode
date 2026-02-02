#!/usr/bin/env node
/**
 * Ralph Output Formatter
 *
 * A richer Node.js alternative to format-output.sh
 * Provides color-coded output, timing, progress spinners, and cleaner formatting
 *
 * Usage: cat stream.json | node output-formatter.js
 */

const readline = require('readline');

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  yellow: '\x1b[33m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  magenta: '\x1b[35m',
  blue: '\x1b[34m',
  white: '\x1b[37m',
};

// Spinner frames
const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
let spinnerIndex = 0;
let spinnerInterval = null;
let currentToolName = '';

// Configuration
const MAX_CONTENT_LENGTH = 500;
const MAX_TOOL_INPUT_LENGTH = 200;

// State
let messageStartTime = null;
let toolStartTime = null;
let totalCost = 0;

function truncate(text, maxLen = MAX_CONTENT_LENGTH) {
  if (!text) return '';
  const str = String(text);
  if (str.length <= maxLen) return str;
  return str.substring(0, maxLen) + '... (truncated)';
}

function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function startSpinner(toolName) {
  currentToolName = toolName;
  stopSpinner();
  spinnerInterval = setInterval(() => {
    const frame = spinnerFrames[spinnerIndex % spinnerFrames.length];
    process.stdout.write(`\r${colors.yellow}${frame}${colors.reset} ${colors.bold}${currentToolName}${colors.reset}  `);
    spinnerIndex++;
  }, 80);
}

function stopSpinner() {
  if (spinnerInterval) {
    clearInterval(spinnerInterval);
    spinnerInterval = null;
    process.stdout.write('\r\x1b[K'); // Clear line
  }
}

function log(prefix, color, message) {
  stopSpinner();
  console.log(`${color}${prefix}${colors.reset} ${message}`);
}

function processLine(line) {
  if (!line.trim()) return;

  let data;
  try {
    data = JSON.parse(line);
  } catch {
    // Not JSON, output as-is
    console.log(line);
    return;
  }

  const type = data.type;

  switch (type) {
    case 'assistant': {
      const content = data.message?.content;
      if (content) {
        if (Array.isArray(content)) {
          content.forEach(block => {
            if (block.type === 'text' && block.text) {
              log('', colors.cyan, block.text);
            }
          });
        } else {
          log('', colors.cyan, content);
        }
      }
      break;
    }

    case 'content_block_start': {
      const blockType = data.content_block?.type;
      if (blockType === 'tool_use') {
        const toolName = data.content_block?.name || 'unknown';
        toolStartTime = Date.now();
        startSpinner(toolName);
      }
      break;
    }

    case 'content_block_delta': {
      const deltaType = data.delta?.type;
      if (deltaType === 'text_delta' && data.delta?.text) {
        stopSpinner();
        process.stdout.write(`${colors.cyan}${data.delta.text}${colors.reset}`);
      }
      // Ignore input_json_delta - it's streaming tool input
      break;
    }

    case 'content_block_stop': {
      // End of content block
      break;
    }

    case 'tool_use': {
      stopSpinner();
      const toolName = data.name || 'unknown';
      const input = data.input ? JSON.stringify(data.input) : '{}';
      log('[tool]', colors.yellow, `${colors.bold}${toolName}${colors.reset}`);
      console.log(`${colors.dim}  input: ${truncate(input, MAX_TOOL_INPUT_LENGTH)}${colors.reset}`);
      toolStartTime = Date.now();
      startSpinner(toolName);
      break;
    }

    case 'tool_result': {
      stopSpinner();
      const isError = data.is_error;
      const duration = toolStartTime ? formatDuration(Date.now() - toolStartTime) : '';

      if (isError) {
        log('[error]', colors.red, `Tool failed ${duration ? `(${duration})` : ''}`);
        if (data.content) {
          console.log(`${colors.red}  ${truncate(data.content, 300)}${colors.reset}`);
        }
      } else {
        log('[done]', colors.green, `Tool completed ${duration ? `(${duration})` : ''}`);
      }
      toolStartTime = null;
      break;
    }

    case 'error': {
      stopSpinner();
      const errorMsg = data.error?.message || data.message || 'Unknown error';
      log('[ERROR]', colors.red, errorMsg);
      break;
    }

    case 'message_start': {
      messageStartTime = Date.now();
      const model = data.message?.model;
      if (model) {
        console.log(`${colors.dim}[model: ${model}]${colors.reset}`);
      }
      break;
    }

    case 'message_stop': {
      stopSpinner();
      console.log('');
      break;
    }

    case 'message_delta': {
      // Message metadata update
      const usage = data.usage;
      if (usage) {
        const tokens = usage.output_tokens || 0;
        console.log(`${colors.dim}[tokens: ${tokens}]${colors.reset}`);
      }
      break;
    }

    case 'system': {
      const text = data.message;
      if (text) {
        log('[system]', colors.magenta, text);
      }
      break;
    }

    case 'result': {
      stopSpinner();
      const cost = data.cost_usd;
      const duration = data.duration_ms;
      const parts = [];
      if (cost) {
        totalCost += parseFloat(cost);
        parts.push(`cost: $${cost}`);
      }
      if (duration) {
        parts.push(`duration: ${formatDuration(duration)}`);
      }
      if (parts.length > 0) {
        console.log(`${colors.dim}[stats] ${parts.join(', ')}${colors.reset}`);
      }
      break;
    }

    default: {
      // Check for subagent info
      if (data.subagent) {
        log('[subagent]', colors.magenta, data.subagent);
      }
      break;
    }
  }
}

// Main
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', processLine);

rl.on('close', () => {
  stopSpinner();
  if (totalCost > 0) {
    console.log(`\n${colors.dim}[session total] $${totalCost.toFixed(4)}${colors.reset}`);
  }
});

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  stopSpinner();
  process.exit(0);
});
