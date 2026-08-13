import type { ServerResponse } from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import consola from 'consola';

export const STATISTICS_RENDERER_PATH = '/api/1/statistics/renderer';

export interface BundleCandidate {
  name: string;
  birthtimeMs: number;
}

/**
 * The newest `.js` file wins, so a rebuild of the premium components is picked
 * up on the next app reload without renaming anything.
 */
export function pickLatestBundle(candidates: BundleCandidate[]): string | undefined {
  let latest: BundleCandidate | undefined;
  for (const candidate of candidates) {
    if (!candidate.name.endsWith('.js'))
      continue;

    if (!latest || candidate.birthtimeMs > latest.birthtimeMs)
      latest = candidate;
  }
  return latest?.name;
}

export function serveStatisticsRenderer(componentsDir: string, res: ServerResponse): void {
  const dist = path.resolve(componentsDir, 'dist');
  const candidates = fs.readdirSync(dist).map(name => ({
    birthtimeMs: fs.statSync(path.join(dist, name)).birthtimeMs,
    name,
  }));

  const latest = pickLatestBundle(candidates);
  const result = latest ? fs.readFileSync(path.join(dist, latest), 'utf8') : '';

  consola.info(`Serving renderer from ${latest ?? '<nothing found>'}`);

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.statusCode = 200;
  res.end(JSON.stringify({
    message: '',
    result,
  }));
}
