import process from 'node:process';
import { Application } from '@electron/main/application';

function ignoreEpipe(err: NodeJS.ErrnoException): void {
  if (err.code === 'EPIPE')
    return;
  throw err;
}

process.stdout.on('error', ignoreEpipe);
process.stderr.on('error', ignoreEpipe);

const app = new Application();

// eslint-disable-next-line unicorn/prefer-top-level-await
app.start().catch((error) => {
  console.error(error);
  process.exit(1);
});
