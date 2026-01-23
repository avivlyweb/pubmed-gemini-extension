#!/usr/bin/env node

/**
 * PubMed MCP Server Wrapper for Gemini CLI
 * Spawns the Python MCP server as a child process
 * 
 * v2.6.0: Added lazy venv creation for GitHub Releases distribution
 * Made by Aviv at Avivly (physiotherapy.ai)
 */

import { spawn, execSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Path to the Python MCP server (in pubmed-mcp subdirectory)
const mcpDir = join(__dirname, 'pubmed-mcp');
const pythonServerPath = join(mcpDir, 'pubmed_mcp.py');
const venvDir = join(mcpDir, 'venv');
const venvPython = join(venvDir, 'bin', 'python3');
const venvPythonWin = join(venvDir, 'Scripts', 'python.exe');
const requirementsPath = join(mcpDir, 'requirements.txt');

// Detect platform
const isWindows = process.platform === 'win32';
const venvPythonPath = isWindows ? venvPythonWin : venvPython;

/**
 * Setup Python virtual environment if it doesn't exist
 * This enables installation via `gemini extensions install` without pre-built venv
 */
async function ensureVenvExists() {
  if (existsSync(venvPythonPath)) {
    return venvPythonPath;
  }

  // First run - need to create venv
  console.error('');
  console.error('  PubMed Extension - First run setup (30 seconds)');
  console.error('  Made by Aviv at Avivly (physiotherapy.ai)');
  console.error('');
  console.error('  Setting up Python environment...');

  try {
    // Find Python command
    let pythonCmd = 'python3';
    try {
      execSync('python3 --version', { stdio: 'pipe' });
    } catch {
      try {
        execSync('python --version', { stdio: 'pipe' });
        pythonCmd = 'python';
      } catch {
        console.error('  ERROR: Python not found. Please install Python 3.9+');
        process.exit(1);
      }
    }

    // Create virtual environment
    console.error('    Creating virtual environment...');
    execSync(`${pythonCmd} -m venv "${venvDir}"`, { 
      cwd: mcpDir, 
      stdio: 'pipe' 
    });

    // Determine pip path
    const pipPath = isWindows 
      ? join(venvDir, 'Scripts', 'pip.exe')
      : join(venvDir, 'bin', 'pip');

    // Install dependencies
    console.error('    Installing dependencies...');
    execSync(`"${pipPath}" install --quiet --upgrade pip`, { 
      cwd: mcpDir, 
      stdio: 'pipe' 
    });
    execSync(`"${pipPath}" install --quiet httpx`, { 
      cwd: mcpDir, 
      stdio: 'pipe' 
    });

    console.error('  Done! Starting server...');
    console.error('');

    return venvPythonPath;
  } catch (error) {
    console.error(`  ERROR: Failed to setup Python environment: ${error.message}`);
    console.error('  Try running the manual installer instead:');
    console.error('  curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash');
    process.exit(1);
  }
}

// Main execution
(async () => {
  // Ensure venv exists (creates on first run)
  const pythonCmd = await ensureVenvExists();

  console.error('Starting PubMed MCP Server...');

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
    process.exit(code);
  });

  pythonProcess.on('error', (err) => {
    console.error(`Failed to start PubMed MCP server: ${err.message}`);
    process.exit(1);
  });

  // Handle parent process termination
  process.on('SIGINT', () => {
    pythonProcess.kill('SIGINT');
  });

  process.on('SIGTERM', () => {
    pythonProcess.kill('SIGTERM');
  });
})();
