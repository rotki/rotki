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

/**
 * Serves the newest premium statistics renderer build, or an empty one.
 *
 * @remarks
 * Every read is synchronous and runs inside the request listener, so an unhandled throw takes the
 * process down, and starling depends on this process for every `/api/1/*` request. `dist`
 * legitimately may not exist yet (components checked out but never built) or may vanish
 * mid-rebuild, so an empty renderer is the answer: the app renders without premium components.
 */
export function serveStatisticsRenderer(componentsDir: string, res: ServerResponse): void {
  const dist = path.resolve(componentsDir, 'dist');

  let result: string = '';
  let latest: string | undefined;
  try {
    const candidates = fs.readdirSync(dist).map(name => ({
      birthtimeMs: fs.statSync(path.join(dist, name)).birthtimeMs,
      name,
    }));
    latest = pickLatestBundle(candidates);
    result = latest ? fs.readFileSync(path.join(dist, latest), 'utf8') : '';
  }
  catch (error: any) {
    consola.warn(`Could not read ${dist}, serving no renderer: ${error.message}`);
  }

  consola.info(`Serving renderer from ${latest ?? '<nothing found>'}`);

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.statusCode = 200;
  res.end(JSON.stringify({
    message: '',
    result,
  }));
}
