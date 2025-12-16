/**
 * Utility to extract icon names from backend Python files
 * Used by vite.config.ts to include dynamically-used icons in the build
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import process from 'node:process';
import { RuiIcons } from '@rotki/ui-library';
import consola from 'consola';

// Regex to match 'lu-...' icon strings in Python files

interface IconLocation {
  file: string;
  line: number;
  icon: string;
}

export interface ScanResult {
  icons: string[];
  invalidIcons: IconLocation[];
}

// Create a Set for O(1) lookup of valid icons
const validIconsSet = new Set<string>(RuiIcons);

/**
 * Recursively get all Python files in a directory, excluding test files
 */
function getPythonFiles(dir: string): string[] {
  const files: string[] = [];

  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);

    if (stat.isDirectory()) {
      // Skip test directories and cache
      if (entry === 'tests' || entry === '__pycache__') {
        continue;
      }
      files.push(...getPythonFiles(fullPath));
    }
    else if (entry.endsWith('.py') && !entry.startsWith('test_')) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Extract icon names from a file with line numbers
 */
function extractIconsWithLocations(filePath: string): IconLocation[] {
  const locations: IconLocation[] = [];
  const content = readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const linePattern = /["']lu-([\da-z-]+)["']/g;

  for (const [lineIndex, line] of lines.entries()) {
    const matches = line.matchAll(linePattern);
    for (const match of matches) {
      locations.push({
        file: filePath,
        line: lineIndex + 1, // 1-indexed
        icon: `lu-${match[1]}`,
      });
    }
  }

  return locations;
}

/**
 * Scan backend Python files and return all unique icon names (sorted) with validation
 */
export function scanBackendIcons(projectRoot: string): ScanResult {
  const backendDir = join(projectRoot, 'rotkehlchen');
  const pythonFiles = getPythonFiles(backendDir);
  const allIcons = new Set<string>();
  const invalidIcons: IconLocation[] = [];

  for (const file of pythonFiles) {
    const locations = extractIconsWithLocations(file);
    for (const location of locations) {
      allIcons.add(location.icon);

      // Check if icon is valid
      if (!validIconsSet.has(location.icon)) {
        invalidIcons.push(location);
      }
    }
  }

  return {
    icons: [...allIcons].sort(),
    invalidIcons,
  };
}

// CLI entry point
if (process.argv[1] === import.meta.filename) {
  const projectRoot = resolve(import.meta.dirname, '../../..');

  consola.info('Scanning backend files for icons...');
  const result = scanBackendIcons(projectRoot);

  consola.info(`Found ${result.icons.length} unique icons:`);
  for (const icon of result.icons) {
    consola.log(`  - ${icon}`);
  }

  if (result.invalidIcons.length > 0) {
    consola.warn(`\nFound ${result.invalidIcons.length} invalid icon(s):`);
    // Group by icon name for cleaner output
    const byIcon = new Map<string, IconLocation[]>();
    for (const loc of result.invalidIcons) {
      const existing = byIcon.get(loc.icon) || [];
      existing.push(loc);
      byIcon.set(loc.icon, existing);
    }

    for (const [icon, locations] of [...byIcon.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      consola.warn(`  ${icon}:`);
      for (const loc of locations) {
        // Make path relative to project root for readability
        const relativePath = loc.file.replace(`${projectRoot}/`, '');
        consola.warn(`    - ${relativePath}:${loc.line}`);
      }
    }
  }
  else {
    consola.success('All icons are valid');
  }
}
