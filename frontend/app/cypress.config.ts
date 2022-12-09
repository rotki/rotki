import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8080',
    fixturesFolder: 'tests/e2e/fixtures',
    specPattern: 'tests/e2e/specs/**/*.spec.ts',
    screenshotsFolder: 'tests/e2e/screenshots',
    videosFolder: 'tests/e2e/videos',
    supportFile: 'tests/e2e/support/index.ts',
    setupNodeEvents(on, config) {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      require('@cypress/code-coverage/task')(on, config);
      // include any other plugin code...
      return config;
    }
  },
  defaultCommandTimeout: 60000,
  responseTimeout: 60000,
  pageLoadTimeout: 300000
});
