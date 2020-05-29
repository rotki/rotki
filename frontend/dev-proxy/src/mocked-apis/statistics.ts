import fs from 'fs';
import path from 'path';
import { Application } from 'express';

export function statistics(server: Application, componentsDir: string): void {
  server.get('/api/1/statistics/renderer', (_, res) => {
    const dist = path.resolve(componentsDir, 'dist');
    const contents = fs.readdirSync(dist);
    let latest = 0;
    let latestFile = '';
    for (let i = 0; i < contents.length; i++) {
      const file = path.join(dist, contents[i]);
      const { birthtimeMs } = fs.statSync(file);
      if (birthtimeMs > latest) {
        latest = birthtimeMs;
        latestFile = file;
      }
    }

    let result = '';
    if (latestFile) {
      result = fs.readFileSync(latestFile, 'utf8');
    }

    console.info(`Serving renderer from ${latestFile}`);

    res.jsonp({
      result,
      message: '',
    });
  });
}
