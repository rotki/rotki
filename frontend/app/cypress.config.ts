import * as process from 'node:process';
import fs from 'node:fs';
import { defineConfig } from 'cypress';

const group = process.env.GROUP ? `${process.env.GROUP}/` : '';
const captureVideo = !!process.env.CI;

export default defineConfig({
  viewportWidth: 1280,
  viewportHeight: 720,
  e2e: {
    baseUrl: 'http://localhost:22230',
    fixturesFolder: 'tests/e2e/fixtures',
    specPattern: `tests/e2e/specs/${group}**/*.spec.ts`,
    screenshotsFolder: 'tests/e2e/screenshots',
    videosFolder: 'tests/e2e/videos',
    supportFile: 'tests/e2e/support/index.ts',
    testIsolation: false,
    video: captureVideo,
    videoCompression: captureVideo,
    scrollBehavior: 'nearest',
    experimentalMemoryManagement: true,
    numTestsKeptInMemory: 5,
    setupNodeEvents(on, config) {
      on(
        'after:spec',
        (spec: Cypress.Spec, results: CypressCommandLine.RunResult) => {
          if (results && results.video && results.tests) {
            // Do we have failures for any retry attempts?
            const failures = results.tests.some(test =>
              test.attempts.some(attempt => attempt.state === 'failed')
            );
            if (!failures) {
              // delete the video if the spec passed and no tests retried
              fs.unlinkSync(results.video);
            }
          }
        }
      );
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
