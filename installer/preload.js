/**
 * Ableton Brain Installer - Preload Script
 * Secure bridge between main and renderer processes
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // Initial state
  getInitialState: () => ipcRenderer.invoke('get-initial-state'),
  
  // Detection
  detectAbleton: () => ipcRenderer.invoke('detect-ableton'),
  browseAbleton: () => ipcRenderer.invoke('browse-ableton'),
  detectPython: () => ipcRenderer.invoke('detect-python'),
  browsePython: () => ipcRenderer.invoke('browse-python'),
  browseUserLibrary: () => ipcRenderer.invoke('browse-user-library'),
  
  // Installation
  runInstallStep: (stepName, args) => ipcRenderer.invoke('run-install-step', stepName, args),
  
  // Services
  launchServices: (args) => ipcRenderer.invoke('launch-services', args),
  stopServices: () => ipcRenderer.invoke('stop-services'),
  openDashboard: () => ipcRenderer.invoke('open-dashboard'),
  openFolder: (path) => ipcRenderer.invoke('open-folder', path),
  checkServices: () => ipcRenderer.invoke('check-services'),
  
  // Auto-updater
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  downloadUpdate: () => ipcRenderer.invoke('download-update'),
  installUpdate: () => ipcRenderer.invoke('install-update'),
  
  // Window controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  
  // Progress events
  onInstallProgress: (callback) => {
    ipcRenderer.on('install-progress', (event, data) => callback(data));
    return () => ipcRenderer.off('install-progress', callback);
  },
  onUpdateStatus: (callback) => {
    ipcRenderer.on('update-status', (event, data) => callback(data));
    return () => ipcRenderer.off('update-status', callback);
  },
  onUpdateDownloadProgress: (callback) => {
    ipcRenderer.on('update-download-progress', (event, data) => callback(data));
    return () => ipcRenderer.off('update-download-progress', callback);
  },
});
