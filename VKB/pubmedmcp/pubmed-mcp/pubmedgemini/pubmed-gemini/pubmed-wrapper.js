#!/usr/bin/env node

/**
 * Nagomi forensic server Wrapper for Gemini CLI
 * Spawns the Python MCP server as a child process
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Path to the Python MCP server (go up to project root, then into pubmed-mcp directory)
const pythonServerPath = join(__dirname, '..', '..', '..', 'pubmed-mcp', 'pubmed_mcp.py');

console.error('Starting Nagomi Forensic Engine...');
console.error(`Backend engine path: ${pythonServerPath}`);

// Spawn the Python process
const pythonProcess = spawn('python3', [pythonServerPath], {
  stdio: ['pipe', 'pipe', 'pipe'],
  cwd: join(__dirname, '..', '..', '..', 'pubmed-mcp'), // Set working directory to pubmed-mcp
  env: {
    ...process.env,
    PYTHONPATH: join(__dirname, '..', '..', '..', 'pubmed-mcp', 'clinical-ai-app', 'backend')
  }
});

// Pipe stdin/stdout/stderr directly
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);
pythonProcess.stderr.pipe(process.stderr);

// Handle process termination
pythonProcess.on('exit', (code) => {
  console.error(`Nagomi Forensic Engine exited with code ${code}`);
  process.exit(code);
});

pythonProcess.on('error', (err) => {
  console.error(`Failed to start Nagomi Forensic Engine: ${err.message}`);
  process.exit(1);
});

// Handle parent process termination
process.on('SIGINT', () => {
  console.error('Terminating Nagomi forensic server...');
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.error('Terminating Nagomi forensic server...');
  pythonProcess.kill('SIGTERM');
});

console.error('Nagomi forensic server wrapper started successfully');
