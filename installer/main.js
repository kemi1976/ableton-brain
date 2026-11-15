/**
 * Ableton Brain Installer - Main Process
 * Auto-detects Ableton, installs Remote Script, sets up Python environment
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const fs = require('fs');
const { spawn, exec } = require('child_process');
const Store = require('electron-store');
const log = require('electron-log');
autoUpdater.logger = log;
autoUpdater.autoDownload = false;
let pty = null; try { pty = require('node-pty'); } catch(e) { console.warn('node-pty not available, terminal features disabled'); }
const os = require('os');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'info';

// Persistent store for installer state
const store = new Store({
  name: 'ableton-brain-installer',
  defaults: {
    abletonPath: '',
    userLibraryPath: '',
    pythonPath: '',
    installStep: 0,
    completedSteps: [],
  }
});

// Platform detection
const isWindows = process.platform === 'win32';
const isMac = process.platform === 'darwin';

// Paths
const RESOURCES_DIR = path.join(__dirname, 'resources');
const REMOTE_SCRIPT_SRC = path.join(RESOURCES_DIR, 'remote_script');
const ANALYZER_SRC = path.join(RESOURCES_DIR, 'analyzer');
const BRAIN_DIR = path.join(__dirname, '..');
const BUNDLED_PYTHON_DIR = !app.isPackaged 
  ? path.join(BRAIN_DIR, 'python', 'dist')
  : path.join(process.resourcesPath, 'python'); // Main ableton-brain folder

let mainWindow = null;
let installPty = null;

// ============================================================================
// ABLETON DETECTION
// ============================================================================

function getDefaultAbletonPaths() {
  const paths = [];
  
  if (isWindows) {
    // Windows common paths
    const programFiles = process.env['ProgramFiles'] || 'C:\\Program Files';
    const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
    const localAppData = process.env['LOCALAPPDATA'];
    
    paths.push(
      path.join(programFiles, 'Ableton', 'Live 12 Suite', 'Program', 'Ableton Live 12 Suite.exe'),
      path.join(programFiles, 'Ableton', 'Live 12 Standard', 'Program', 'Ableton Live 12 Standard.exe'),
      path.join(programFiles, 'Ableton', 'Live 11 Suite', 'Program', 'Ableton Live 11 Suite.exe'),
      path.join(programFiles, 'Ableton', 'Live 11 Standard', 'Program', 'Ableton Live 11 Standard.exe'),
      path.join(programFilesX86, 'Ableton', 'Live 12 Suite', 'Program', 'Ableton Live 12 Suite.exe'),
      path.join(programFilesX86, 'Ableton', 'Live 11 Suite', 'Program', 'Ableton Live 11 Suite.exe'),
      path.join(localAppData, 'Ableton', 'Live 12 Suite', 'Program', 'Ableton Live 12 Suite.exe'),
      path.join(localAppData, 'Ableton', 'Live 11 Suite', 'Program', 'Ableton Live 11 Suite.exe')
    );
  } else {
    // macOS common paths
    paths.push(
      '/Applications/Ableton Live 12 Suite/Ableton Live 12 Suite.app',
      '/Applications/Ableton Live 12 Standard/Ableton Live 12 Standard.app',
      '/Applications/Ableton Live 11 Suite/Ableton Live 11 Suite.app',
      '/Applications/Ableton Live 11 Standard/Ableton Live 11 Standard.app'
    );
  }
  
  return paths;
}

function getUserLibraryPath() {
  if (isWindows) {
    const docs = process.env['USERPROFILE'] 
      ? path.join(process.env['USERPROFILE'], 'Documents')
      : path.join(os.homedir(), 'Documents');
    return path.join(docs, 'Ableton', 'User Library');
  } else {
    return path.join(os.homedir(), 'Music', 'Ableton', 'User Library');
  }
}

async function detectAbleton() {
  const paths = getDefaultAbletonPaths();
  
  for (const p of paths) {
    try {
      await fs.promises.access(p);
      log.info(`Found Ableton at: ${p}`);
      return p;
    } catch {
      continue;
    }
  }
  
  return null;
}

function getAbletonVersion(abletonPath) {
  // Extract version from path
  const match = abletonPath.match(/Live (\d+)/);
  return match ? parseInt(match[1]) : 11;
}

// ============================================================================
// PYTHON DETECTION & SETUP
// ============================================================================

async function getBundledPythonPath() {
  const bundledPaths = [
    path.join(BUNDLED_PYTHON_DIR, 'ableton-brain-mcp'),
    path.join(BUNDLED_PYTHON_DIR, 'ableton-brain-mcp.exe'),
    path.join(BUNDLED_PYTHON_DIR, 'python', 'bin', 'python'),
    path.join(BUNDLED_PYTHON_DIR, 'python', 'Scripts', 'python.exe'),
  ];

  for (const p of bundledPaths) {
    if (fs.existsSync(p)) {
      log.info(`Found bundled Python/runtime at: ${p}`);
      return p;
    }
  }

  return null;
}

function detectPython() {
  // Try common Python paths
  const candidates = [];
  
  if (isWindows) {
    candidates.push(
      path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'python.exe'),
      path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
      'python',
      'python3'
    );
  } else {
    candidates.push(
      '/usr/local/bin/python3.13',
      '/usr/local/bin/python3.12',
      '/usr/local/bin/python3.11',
      '/opt/homebrew/bin/python3.13',
      '/opt/homebrew/bin/python3.12',
      'python3',
      'python'
    );
  }
  
  for (const candidate of candidates) {
    try {
      const result = await runCommand(candidate, ['--version']);
      if (result.stdout.includes('Python 3.1') || result.stdout.includes('Python 3.1')) {
        const versionMatch = result.stdout.match(/Python (\d+\.\d+)/);
        if (versionMatch) {
          const version = parseFloat(versionMatch[1]);
          if (version >= 3.10) {
            log.info(`Found Python ${versionMatch[1]} at: ${candidate}`);
            return candidate;
          }
        }
      }
    } catch {
      continue;
    }
  }
  
  return null;
}

function runCommand(cmd, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      windowsHide: true,
      ...options
    });
    
    let stdout = '';
    let stderr = '';
    
    child.stdout.on('data', (data) => stdout += data.toString());
    child.stderr.on('data', (data) => stderr += data.toString());
    
    child.on('close', (code) => {
      resolve({ code, stdout, stderr });
    });
    
    child.on('error', (err) => {
      reject(err);
    });
  });
}

// ============================================================================
// INSTALLATION STEPS
// ============================================================================

async function installRemoteScript(userLibraryPath, progressCallback) {
  const remoteScriptDir = path.join(userLibraryPath, 'Remote Scripts', 'AbletonBrain');
  
  progressCallback(10, 'Creating Remote Scripts folder...');
  await fs.promises.mkdir(remoteScriptDir, { recursive: true });
  
  progressCallback(30, 'Copying Remote Script...');
  // Copy our remote script
  const srcFiles = await fs.promises.readdir(REMOTE_SCRIPT_SRC);
  for (const file of srcFiles) {
    await fs.promises.copyFile(
      path.join(REMOTE_SCRIPT_SRC, file),
      path.join(remoteScriptDir, file)
    );
  }
  
  // Also copy the analyzer bridge if needed
  progressCallback(50, 'Installing dependencies...');
  
  progressCallback(90, 'Verifying installation...');
  const installedFiles = await fs.promises.readdir(remoteScriptDir);
  
  progressCallback(100, 'Remote Script installed successfully!');
  return { success: true, path: remoteScriptDir, files: installedFiles };
}

async function installAnalyzerDevice(userLibraryPath, progressCallback) {
  const analyzerDir = path.join(userLibraryPath, 'Presets', 'Audio Effects', 'Max Audio Effect');
  
  progressCallback(20, 'Creating Max for Live presets folder...');
  await fs.promises.mkdir(analyzerDir, { recursive: true });
  
  progressCallback(50, 'Checking for Analyzer device...');
  const analyzerFiles = await fs.promises.readdir(ANALYZER_SRC).catch(() => []);
  
  if (analyzerFiles.length > 0) {
    progressCallback(70, 'Copying Analyzer device...');
    for (const file of analyzerFiles) {
      if (file.endsWith('.amxd') || file.endsWith('.maxpat')) {
        await fs.promises.copyFile(
          path.join(ANALYZER_SRC, file),
          path.join(analyzerDir, file)
        );
      }
    }
  }
  
  progressCallback(100, 'Analyzer device ready (install .amxd manually if needed)');
  return { success: true, path: analyzerDir };
}

async function setupPythonEnvironment(pythonPath, brainDir, progressCallback) {
  const venvDir = path.join(brainDir, '.venv');
  
  progressCallback(10, 'Creating virtual environment...');
  const result = await runCommand(pythonPath, ['-m', 'venv', venvDir]);
  if (result.code !== 0) {
    throw new Error(`Failed to create venv: ${result.stderr}`);
  }
  
  const venvPython = isWindows
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');
  
  progressCallback(30, 'Upgrading pip...');
  await runCommand(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip']);
  
  progressCallback(50, 'Installing core dependencies...');
  const coreDeps = [
    'mcp', 'fastapi', 'uvicorn', 'librosa', 'numpy', 'scipy',
    'python-osc', 'pyloudnorm', 'soundfile', 'mido', 'requests',
    'websocket-client', 'anyio', 'rich', 'qrcode', 'Pillow',
    'pytest', 'pytest-asyncio', 'faiss-cpu'
  ];
  
  // Install in batches to show progress
  const batchSize = 3;
  for (let i = 0; i < coreDeps.length; i += batchSize) {
    const batch = coreDeps.slice(i, i + batchSize);
    await runCommand(venvPython, ['-m', 'pip', 'install', ...batch]);
    progressCallback(50 + Math.round((i / coreDeps.length) * 40), `Installing: ${batch.join(', ')}`);
  }
  
  progressCallback(95, 'Installing optional GPU dependencies...');
  // Try to install GPU deps (may fail on CPU-only machines)
  try {
    await runCommand(venvPython, ['-m', 'pip', 'install', 'torch', 'torchaudio', '--index-url', 'https://download.pytorch.org/whl/cu118']);
  } catch {
    log.warn('GPU dependencies not installed (CUDA not available)');
  }
  
  progressCallback(100, 'Python environment ready!');
  return { success: true, venvPath: venvDir, venvPython };
}

async function configureMCPClient(venvPython, brainDir, progressCallback) {
  progressCallback(50, 'Generating MCP configuration...');
  
  const config = {
    mcpServers: {
      "ableton-brain": {
        command: venvPython,
        args: [path.join(brainDir, 'mcp_server.py')]
      }
    }
  };
  
  // Determine config file location based on platform
  let configPath;
  if (isWindows) {
    configPath = path.join(process.env['APPDATA'], 'Claude', 'claude_desktop_config.json');
  } else {
    configPath = path.join(os.homedir(), 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
  }
  
  progressCallback(80, `Writing config to ${configPath}...`);
  
  // Read existing config or create new
  let existingConfig = { mcpServers: {} };
  try {
    const content = await fs.promises.readFile(configPath, 'utf8');
    existingConfig = JSON.parse(content);
  } catch {
    // Config doesn't exist, use default
  }
  
  // Merge configs
  existingConfig.mcpServers = {
    ...existingConfig.mcpServers,
    ...config.mcpServers
  };
  
  await fs.promises.mkdir(path.dirname(configPath), { recursive: true });
  await fs.promises.writeFile(configPath, JSON.stringify(existingConfig, null, 2));
  
  progressCallback(100, 'MCP configuration complete!');
  return { success: true, configPath };
}


// ============================================================================
// AUTO-UPDATER SETUP
// ============================================================================

function setupAutoUpdater() {
  const isDev = !app.isPackaged;
  if (isDev || !store.get('autoUpdateEnabled')) return;

  autoUpdater.on('checking-for-update', () => {
    log.info('Checking for update...');
    mainWindow?.webContents.send('update-status', { status: 'checking' });
  });

  autoUpdater.on('update-available', (info) => {
    log.info('Update available:', info.version);
    mainWindow?.webContents.send('update-status', { 
      status: 'available', 
      version: info.version,
      releaseNotes: info.releaseNotes,
      releaseDate: info.releaseDate
    });
  });

  autoUpdater.on('update-not-available', (info) => {
    log.info('Update not available:', info.version);
    mainWindow?.webContents.send('update-status', { status: 'not-available', version: info.version });
  });

  autoUpdater.on('error', (err) => {
    log.error('Auto-updater error:', err);
    mainWindow?.webContents.send('update-status', { status: 'error', error: err.message });
  });

  autoUpdater.on('download-progress', (progressObj) => {
    mainWindow?.webContents.send('update-download-progress', progressObj);
  });

  autoUpdater.on('update-downloaded', (info) => {
    log.info('Update downloaded');
    mainWindow?.webContents.send('update-status', { 
      status: 'downloaded', 
      version: info.version 
    });
    autoUpdater.quitAndInstall(false, true);
  });

  autoUpdater.checkForUpdates();
  setInterval(() => autoUpdater.checkForUpdates(), 4 * 60 * 60 * 1000);
}

ipcMain.handle('check-for-updates', async () => {
  const isDev = !app.isPackaged;
  if (isDev) return { status: 'dev-mode' };
  try {
    const result = await autoUpdater.checkForUpdates();
    return { status: 'checked', updateInfo: result?.updateInfo };
  } catch (err) {
    return { status: 'error', error: err.message };
  }
});

ipcMain.handle('download-update', async () => {
  const isDev = !app.isPackaged;
  if (isDev) return { status: 'dev-mode' };
  try {
    await autoUpdater.downloadUpdate();
    return { status: 'downloading' };
  } catch (err) {
    return { status: 'error', error: err.message };
  }
});

ipcMain.handle('install-update', async () => {
  const isDev = !app.isPackaged;
  if (isDev) return { status: 'dev-mode' };
  autoUpdater.quitAndInstall(false, true);
  return { status: 'installing' };
});

// ============================================================================
// MAIN WINDOW
// ============================================================================

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 800,
    minHeight: 600,
    title: 'Ableton Brain Installer',
    icon: path.join(RESOURCES_DIR, isWindows ? 'icon.ico' : 'icon.icns'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      backgroundThrottling: false
    },
    show: false,
    frame: false,
    titleBarStyle: 'hidden',
    trafficLightPosition: { x: 15, y: 15 }
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  
  mainWindow.once('ready-to-show', () => {
    setupAutoUpdater();
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle window controls
  ipcMain.on('window-minimize', () => mainWindow.minimize());
  ipcMain.on('window-maximize', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });
  ipcMain.on('window-close', () => mainWindow.close());

  return mainWindow;
}

// ============================================================================
// IPC HANDLERS
// ============================================================================

ipcMain.handle('get-initial-state', async () => {
  return {
    platform: process.platform,
    abletonPath: store.get('abletonPath'),
    userLibraryPath: store.get('userLibraryPath') || getUserLibraryPath(),
    pythonPath: store.get('pythonPath'),
    installStep: store.get('installStep'),
    completedSteps: store.get('completedSteps'),
    brainDir: BRAIN_DIR
  };
});

ipcMain.handle('detect-ableton', async () => {
  const abletonPath = await detectAbleton();
  const userLibraryPath = getUserLibraryPath();
  
  if (abletonPath) {
    store.set('abletonPath', abletonPath);
    store.set('userLibraryPath', userLibraryPath);
  }
  
  return { abletonPath, userLibraryPath, version: abletonPath ? getAbletonVersion(abletonPath) : null };
});

ipcMain.handle('browse-ableton', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Ableton Live Application',
    filters: [
      { name: 'Ableton Live', extensions: isWindows ? ['exe'] : ['app'] }
    ],
    properties: ['openFile']
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const abletonPath = result.filePaths[0];
    store.set('abletonPath', abletonPath);
    return { abletonPath, version: getAbletonVersion(abletonPath) };
  }
  
  return null;
});

ipcMain.handle('detect-python', async () => {
  const pythonPath = await detectPython();
  if (pythonPath) {
    store.set('pythonPath', pythonPath);
  }
  return { pythonPath };
});

ipcMain.handle('browse-python', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Python Executable',
    filters: [
      { name: 'Python', extensions: isWindows ? ['exe'] : [] }
    ],
    properties: ['openFile']
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const pythonPath = result.filePaths[0];
    store.set('pythonPath', pythonPath);
    return { pythonPath };
  }
  
  return null;
});

ipcMain.handle('browse-user-library', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Ableton User Library Folder',
    properties: ['openDirectory']
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const userLibraryPath = result.filePaths[0];
    store.set('userLibraryPath', userLibraryPath);
    return { userLibraryPath };
  }
  
  return null;
});

ipcMain.handle('run-install-step', async (event, stepName, args) => {
  const sendProgress = (progress, message) => {
    mainWindow.webContents.send('install-progress', { step: stepName, progress, message });
  };
  
  try {
    let result;
    
    switch (stepName) {
      case 'remoteScript':
        result = await installRemoteScript(args.userLibraryPath, sendProgress);
        break;
      case 'analyzerDevice':
        result = await installAnalyzerDevice(args.userLibraryPath, sendProgress);
        break;
      case 'pythonEnvironment':
        result = await setupPythonEnvironment(args.pythonPath, args.brainDir, sendProgress);
        store.set('venvPath', result.venvPath);
        store.set('venvPython', result.venvPython);
        break;
      case 'mcpConfig':
        result = await configureMCPClient(args.venvPython, args.brainDir, sendProgress);
        break;
      default:
        throw new Error(`Unknown step: ${stepName}`);
    }
    
    // Mark step as completed
    const completed = store.get('completedSteps') || [];
    if (!completed.includes(stepName)) {
      completed.push(stepName);
      store.set('completedSteps', completed);
    }
    
    return { success: true, result };
  } catch (error) {
    log.error(`Install step ${stepName} failed:`, error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('launch-services', async (event, args) => {
  const venvPython = store.get('venvPython');
  const brainDir = BRAIN_DIR;
  
  if (!venvPython) {
    return { success: false, error: 'Python environment not set up' };
  }
  
  // Launch MCP server
  const mcpProcess = spawn(venvPython, ['mcp_server.py', '--http'], {
    cwd: brainDir,
    detached: true,
    stdio: 'ignore'
  });
  mcpProcess.unref();
  
  // Launch analyzer bridge
  const analyzerProcess = spawn(venvPython, ['analyzer_bridge.py'], {
    cwd: brainDir,
    detached: true,
    stdio: 'ignore'
  });
  analyzerProcess.unref();
  
  // Launch fleet coordinator
  const fleetProcess = spawn(venvPython, ['fleet_coordinator.py'], {
    cwd: brainDir,
    detached: true,
    stdio: 'ignore'
  });
  fleetProcess.unref();
  
  // Open dashboard
  setTimeout(() => {
    shell.openExternal('http://localhost:8050');
  }, 2000);
  
  return { success: true };
});

ipcMain.handle('open-dashboard', async () => {
  shell.openExternal('http://localhost:8050');
  return { success: true };
});

ipcMain.handle('open-folder', async (event, folderPath) => {
  shell.openPath(folderPath);
  return { success: true };
});

ipcMain.handle('check-services', async () => {
  try {
    const response = await fetch('http://localhost:8050/health');
    const data = await response.json();
    return { running: true, ...data };
  } catch {
    return { running: false };
  }
});

// ============================================================================
// APP LIFECYCLE
// ============================================================================

app.whenReady().then(() => {
  createMainWindow();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (!isMac) {
    app.quit();
  }
});

app.on('before-quit', () => {
  // Clean up any running processes
  if (installPty) {
    installPty.kill();
  }
});

// Security: Prevent navigation to external URLs
app.on('web-contents-created', (event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    if (parsedUrl.origin !== 'file://') {
      event.preventDefault();
    }
  });
});