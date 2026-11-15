const fs = require('fs');
const path = require('path');

async function sign(context) {
  const { appOutDir, platform, electronPlatformName, packager } = context;
  
  console.log(`After sign hook: platform=${platform}, appOutDir=${appOutDir}`);
  
  // Notarization for macOS
  if (platform === 'darwin' && process.env.APPLE_ID && process.env.APPLE_ID_PASSWORD) {
    const { notarize } = require('@electron/notarize');
    await notarize({
      tool: 'notarytool',
      appBundleId: 'com.abletonbrain.installer',
      appPath: path.join(appOutDir, `${packager.appInfo.productName}.app`),
      appleId: process.env.APPLE_ID,
      appleIdPassword: process.env.APPLE_ID_PASSWORD,
      teamId: process.env.APPLE_TEAM_ID,
    });
    console.log('Notarization complete');
  }
  
  // Windows timestamping (optional)
  if (platform === 'win32' && process.env.SIGNTOOL_PATH) {
    const { execSync } = require('child_process');
    const exePath = path.join(appOutDir, 'Ableton Brain Installer.exe');
    if (fs.existsSync(exePath)) {
      execSync(`"${process.env.SIGNTOOL_PATH}" sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 "${exePath}"`);
      console.log('Timestamp applied');
    }
  }
}

module.exports = sign;
