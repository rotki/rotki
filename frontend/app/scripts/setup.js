const path = require('node:path');

/** @type 'production' | 'development'' */
const mode = (process.env.NODE_ENV = process.env.NODE_ENV || 'development');

/** @type {import('vite').LogLevel} */
const LOG_LEVEL = 'info';

/** @type {import('vite').InlineConfig} */
const sharedConfig = {
  mode,
  logLevel: LOG_LEVEL
};

// in some systems the virtualenv's python is not detected from inside electron and the
// system python is used. Electron/node seemed to add /usr/bin to the path before the
// virtualenv directory and as such system's python is used. Not sure why this happens only
// in some systems. Check again in the future if this happens in Lefteris laptop Archlinux.
// To mitigate this if a virtualenv is detected we add its bin directory to the start of the path.
if (process.env.VIRTUAL_ENV) {
  process.env.PATH = process.env.VIRTUAL_ENV.concat(
    path.sep,
    process.platform === 'win32' ? 'Scripts;' : 'bin:',
    process.env.PATH
  );
}

module.exports = {
  mode,
  LOG_LEVEL,
  sharedConfig
};
