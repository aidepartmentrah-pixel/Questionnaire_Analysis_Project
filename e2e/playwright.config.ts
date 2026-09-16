import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const repoRoot = path.resolve(import.meta.dirname, '..')
const backendDir = path.join(repoRoot, 'backend')
const frontendDir = path.join(repoRoot, 'frontend')

const venvPython =
  process.platform === 'win32'
    ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
    : path.join(backendDir, '.venv', 'bin', 'python')

// Fall back to whatever "python"/"uvicorn" is on PATH if the local venv
// hasn't been created yet (e.g. a from-scratch CI runner that installs
// dependencies globally instead of into backend/.venv).
const pythonBin = fs.existsSync(venvPython) ? venvPython : 'python'

const isCI = !!process.env.CI

export default defineConfig({
  testDir: './tests',
  // The backend keeps exactly one active dataset in a single in-process slot
  // (by product design - see docs/PROGRESS.md). Any two tests that upload a
  // dataset would race if run concurrently against that shared backend, so
  // the whole suite runs on a single worker instead of trying to keep every
  // spec file mutually non-interfering.
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }]],
  timeout: 30_000,

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: `"${pythonBin}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: !isCI,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --port 5173 --strictPort',
      cwd: frontendDir,
      url: 'http://localhost:5173',
      reuseExistingServer: !isCI,
      timeout: 60_000,
    },
  ],
})
