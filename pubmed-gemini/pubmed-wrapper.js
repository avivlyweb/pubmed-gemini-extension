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

// Path to the Python MCP server (sibling directory pubmed-mcp)
const pythonServerPath = join(__dirname, '..', 'pubmed-mcp', 'pubmed_mcp.py');
const mcpDir = join(__dirname, '..', 'pubmed-mcp');

console.error('Starting PubMed MCP Server...');
console.error(`Python server path: ${pythonServerPath}`);

// Spawn the Python process
const pythonProcess = spawn('python3', [pythonServerPath], {
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
