import type { ServerResponse } from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import consola from 'consola';

export const STATISTICS_RENDERER_PATH = '/api/1/statistics/renderer';

/**
 * Serves the newest `.js` file (by birthtime) from `<componentsDir>/dist`, so a
 * rebuild of the premium components is picked up on the next app reload.
 */
export function serveStatisticsRenderer(componentsDir: string, res: ServerResponse): void {
  const dist = path.resolve(componentsDir, 'dist');
  const contents = fs.readdirSync(dist);
  let latest = 0;
  let latestFile = '';
  for (const content of contents) {
    if (!content.endsWith('.js')) {
      continue;
    }
    const file = path.join(dist, content);
    const { birthtimeMs } = fs.statSync(file);
    if (birthtimeMs > latest) {
      latest = birthtimeMs;
      latestFile = file;
    }
  }

  let result = '';
  if (latestFile)
    result = fs.readFileSync(latestFile, 'utf8');

  consola.info(`Serving renderer from ${latestFile}`);

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.statusCode = 200;
  res.end(JSON.stringify({
    message: '',
    result,
  }));
}
