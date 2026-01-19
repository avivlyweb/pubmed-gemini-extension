#!/usr/bin/env node

/**
 * PubMed MCP Server Wrapper for Gemini CLI
 * Spawns the Python MCP server as a child process
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Path to the Python MCP server (in pubmed-mcp subdirectory)
const mcpDir = join(__dirname, 'pubmed-mcp');
const pythonServerPath = join(mcpDir, 'pubmed_mcp.py');
const venvPython = join(mcpDir, 'venv', 'bin', 'python3');

console.error('Starting PubMed MCP Server...');
console.error(`Python server path: ${pythonServerPath}`);

// Use venv python if available, otherwise system python3
import { existsSync } from 'fs';
const pythonCmd = existsSync(venvPython) ? venvPython : 'python3';
console.error(`Using Python: ${pythonCmd}`);

// Spawn the Python process
const pythonProcess = spawn(pythonCmd, [pythonServerPath], {
  stdio: ['pipe', 'pipe', 'pipe'],
  cwd: mcpDir,
  env: {
    ...process.env,
    PYTHONPATH: mcpDir
  }
});

// Pipe stdin/stdout/stderr directly
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);
pythonProcess.stderr.pipe(process.stderr);

// Handle process termination
pythonProcess.on('exit', (code) => {
  console.error(`PubMed MCP server exited with code ${code}`);
  process.exit(code);
});

pythonProcess.on('error', (err) => {
  console.error(`Failed to start PubMed MCP server: ${err.message}`);
  process.exit(1);
});

// Handle parent process termination
process.on('SIGINT', () => {
  console.error('Terminating PubMed MCP server...');
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.error('Terminating PubMed MCP server...');
  pythonProcess.kill('SIGTERM');
});

console.error('PubMed MCP Server wrapper started successfully');
