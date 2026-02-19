const { build } = require('electron-builder');
const fs = require('fs-extra');
const path = require('path');

async function buildElectronApp() {
  console.log('Building Electron application...');
  
  try {
    // Copy production main.js over the development version
    await fs.copy('main-production.js', 'main.js');
    console.log('Copied production main.js');
    
    // Ensure required directories exist
    await fs.ensureDir('uploads');
    await fs.ensureDir('reports');
    console.log('Ensured directories exist');
    
    // Build configuration
    const config = {
      appId: 'com.contractanalysis.tool',
      productName: 'Contract Analysis Tool',
      directories: {
        output: 'dist',
        buildResources: 'build'
      },
      files: [
        'main.js',
        'app.py',
        'agent*.py',
        'static/**/*',
        'templates/**/*',
        'seller*.md',
        'pyproject.toml',
        'uv.lock',
        'uploads/',
        'reports/'
      ],
      extraFiles: [
        {
          from: 'uploads',
          to: 'uploads'
        },
        {
          from: 'reports', 
          to: 'reports'
        }
      ],
      win: {
        target: [
          {
            target: 'nsis',
            arch: ['x64']
          },
          {
            target: 'portable',
            arch: ['x64']
          }
        ],
        icon: 'static/logo.png'
      },
      mac: {
        target: [
          {
            target: 'dmg',
            arch: ['x64', 'arm64']
          }
        ],
        icon: 'static/logo.png',
        category: 'public.app-category.business'
      },
      linux: {
        target: [
          {
            target: 'AppImage',
            arch: ['x64']
          },
          {
            target: 'deb',
            arch: ['x64']
          }
        ],
        icon: 'static/logo.png',
        category: 'Office'
      },
      nsis: {
        oneClick: false,
        allowToChangeInstallationDirectory: true,
        createDesktopShortcut: true,
        createStartMenuShortcut: true
      },
      publish: null // Don't auto-publish
    };
    
    // Build for current platform
    await build({
      config,
      publish: 'never'
    });
    
    console.log('✅ Electron build completed successfully!');
    console.log('📦 Build artifacts are in the dist/ directory');
    
  } catch (error) {
    console.error('❌ Build failed:', error);
    process.exit(1);
  }
}

// Run the build
buildElectronApp();