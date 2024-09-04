import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const __dirname = import.meta.dirname;
const rootDir = path.join(__dirname, '..');

const sourceFile = path.join(rootDir, 'node_modules', 'vue', 'dist', 'vue.global.prod.js');
const destDir = path.join(rootDir, 'public', 'address-import', 'js');
const destFile = path.join(destDir, 'vue.global.prod.js');

// Ensure the destination directory exists
fs.mkdir(destDir, { recursive: true }, (err) => {
  if (err) {
    console.error('Error creating directory:', err);
    process.exit(1);
  }

  // Copy the file
  fs.copyFile(sourceFile, destFile, (err) => {
    if (err) {
      console.error('Error copying file:', err);
      process.exit(1);
    }
    console.log('Vue.js file successfully copied to public/address-import/js/');
  });
});
