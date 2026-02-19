const { app, BrowserWindow, Menu, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let flaskProcess;

// Configuration
const FLASK_PORT = 5000;
const FLASK_HOST = '127.0.0.1';
const isDev = process.env.NODE_ENV === 'development';

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true
    },
    icon: getIconPath(),
    title: 'Contract Analysis Tool',
    show: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default'
  });

  // Set up application menu
  setupMenu();

  // Wait for Flask server to be ready, then load the app
  waitForFlask(() => {
    mainWindow.loadURL(`http://${FLASK_HOST}:${FLASK_PORT}`);
    mainWindow.show();
    
    if (isDev) {
      mainWindow.webContents.openDevTools();
    }
  });

  // Handle window events
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.on('unresponsive', () => {
    dialog.showMessageBox(mainWindow, {
      type: 'warning',
      title: 'Application Not Responding',
      message: 'The application appears to be unresponsive. Would you like to restart?',
      buttons: ['Wait', 'Restart'],
      defaultId: 0
    }).then((result) => {
      if (result.response === 1) {
        app.relaunch();
        app.exit();
      }
    });
  });
}

function getIconPath() {
  const iconName = process.platform === 'win32' ? 'logo.ico' : 'logo.png';
  const iconPath = path.join(__dirname, 'static', iconName);
  
  // Fallback to default if custom icon doesn't exist
  if (fs.existsSync(iconPath)) {
    return iconPath;
  }
  return undefined;
}

function setupMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Analysis',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.executeJavaScript('window.location.reload()');
            }
          }
        },
        { type: 'separator' },
        {
          label: 'Open Reports Folder',
          click: () => {
            const { shell } = require('electron');
            shell.openPath(path.join(__dirname, 'reports'));
          }
        },
        { type: 'separator' },
        {
          label: 'Exit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit();
          }
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        ...(isDev ? [{ role: 'toggleDevTools' }] : []),
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About Contract Analysis Tool',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About Contract Analysis Tool',
              message: 'Contract Analysis Tool',
              detail: 'A desktop application for analyzing contracts and generating compliance reports.\n\nVersion: 1.0.0\nBuilt with Electron and Flask'
            });
          }
        },
        {
          label: 'View Logs',
          click: () => {
            const { shell } = require('electron');
            const logPath = path.join(app.getPath('userData'), 'logs');
            shell.openPath(logPath);
          }
        }
      ]
    }
  ];

  // macOS specific menu adjustments
  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    });
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function startFlaskServer() {
  console.log('Starting Flask server...');
  
  // Determine Python executable
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  
  // Start the Flask server using gunicorn (Unix) or direct Flask (Windows)
  const isWindows = process.platform === 'win32';
  const cmd = isWindows ? pythonCmd : 'gunicorn';
  const args = isWindows 
    ? ['-m', 'gunicorn', '--bind', `${FLASK_HOST}:${FLASK_PORT}`, '--workers', '1', '--timeout', '300', 'main:app']
    : ['--bind', `${FLASK_HOST}:${FLASK_PORT}`, '--workers', '1', '--timeout', '300', 'main:app'];

  flaskProcess = spawn(cmd, args, {
    cwd: __dirname,
    stdio: 'pipe',
    env: {
      ...process.env,
      PYTHONPATH: __dirname,
      SESSION_SECRET: 'electron-production-secret'
    }
  });

  flaskProcess.stdout.on('data', (data) => {
    console.log(`Flask stdout: ${data}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.log(`Flask stderr: ${data}`);
  });

  flaskProcess.on('close', (code) => {
    console.log(`Flask process exited with code ${code}`);
    if (code !== 0 && mainWindow) {
      dialog.showErrorBox(
        'Server Error',
        'The backend server stopped unexpectedly. Please restart the application.'
      );
    }
  });

  flaskProcess.on('error', (err) => {
    console.error('Failed to start Flask server:', err);
    dialog.showErrorBox(
      'Startup Error',
      `Failed to start the backend server: ${err.message}`
    );
    app.quit();
  });
}

function waitForFlask(callback) {
  const maxAttempts = 30;
  let attempts = 0;

  const checkFlask = () => {
    const http = require('http');
    const req = http.get(`http://${FLASK_HOST}:${FLASK_PORT}`, (res) => {
      console.log('Flask server is ready');
      callback();
    });

    req.on('error', () => {
      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(checkFlask, 1000);
      } else {
        console.error('Failed to connect to Flask server after 30 attempts');
        dialog.showErrorBox(
          'Connection Error',
          'Failed to connect to the backend server. Please check your installation.'
        );
        app.quit();
      }
    });

    req.setTimeout(1000, () => {
      req.abort();
    });
  };

  setTimeout(checkFlask, 3000); // Initial delay to let Flask start
}

function killFlaskServer() {
  if (flaskProcess) {
    console.log('Stopping Flask server...');
    
    if (process.platform === 'win32') {
      // On Windows, kill the process tree
      spawn('taskkill', ['/pid', flaskProcess.pid, '/f', '/t']);
    } else {
      flaskProcess.kill('SIGTERM');
    }
    
    flaskProcess = null;
  }
}

// App event handlers
app.whenReady().then(() => {
  // Set app user model ID for Windows
  if (process.platform === 'win32') {
    app.setAppUserModelId('com.contractanalysis.tool');
  }
  
  startFlaskServer();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  killFlaskServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  killFlaskServer();
});

// Handle app termination
process.on('SIGINT', () => {
  killFlaskServer();
  process.exit(0);
});

process.on('SIGTERM', () => {
  killFlaskServer();
  process.exit(0);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  killFlaskServer();
  app.quit();
});