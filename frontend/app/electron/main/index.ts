import process from 'node:process';
import { Application } from '@electron/main/application';

const app = new Application();

// eslint-disable-next-line unicorn/prefer-top-level-await
app.start().catch((error) => {
  console.error(error);
  process.exit(1);
});
