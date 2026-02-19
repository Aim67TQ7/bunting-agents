const { app, BrowserWindow, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let mainWindow;
let flaskProcess;

// Flask server configuration
const FLASK_PORT = 5000;
const FLASK_HOST = '127.0.0.1';

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true
    },
    icon: path.join(__dirname, 'static', 'logo.png'),
    title: 'Contract Analysis Tool',
    show: false // Don't show until ready
  });

  // Set up application menu
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Analysis',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            mainWindow.webContents.executeJavaScript('window.location.reload()');
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
        { role: 'toggleDevTools' },
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
          label: 'About',
          click: () => {
            require('electron').dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About Contract Analysis Tool',
              message: 'Contract Analysis Tool v1.0.0',
              detail: 'A desktop application for analyzing contracts and generating compliance reports.'
            });
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

  // Wait for Flask server to be ready, then load the app
  waitForFlask(() => {
    mainWindow.loadURL(`http://${FLASK_HOST}:${FLASK_PORT}`);
    mainWindow.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startFlaskServer() {
  console.log('Starting Flask server...');
  
  // Start the Flask server using gunicorn
  flaskProcess = spawn('gunicorn', [
    '--bind', `${FLASK_HOST}:${FLASK_PORT}`,
    '--workers', '1',
    '--timeout', '300',
    'main:app'
  ], {
    cwd: __dirname,
    stdio: 'pipe'
  });

  flaskProcess.stdout.on('data', (data) => {
    console.log(`Flask stdout: ${data}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.log(`Flask stderr: ${data}`);
  });

  flaskProcess.on('close', (code) => {
    console.log(`Flask process exited with code ${code}`);
  });
}

function waitForFlask(callback) {
  const maxAttempts = 30;
  let attempts = 0;

  const checkFlask = () => {
    const http = require('http');
    const req = http.get(`http://${FLASK_HOST}:${FLASK_PORT}`, (res) => {
      callback();
    });

    req.on('error', () => {
      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(checkFlask, 1000);
      } else {
        console.error('Failed to connect to Flask server after 30 attempts');
        app.quit();
      }
    });

    req.setTimeout(1000, () => {
      req.abort();
    });
  };

  setTimeout(checkFlask, 2000); // Initial delay to let Flask start
}

function killFlaskServer() {
  if (flaskProcess) {
    console.log('Stopping Flask server...');
    flaskProcess.kill('SIGTERM');
    flaskProcess = null;
  }
}

// App event handlers
app.whenReady().then(() => {
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