import * as process from 'node:process';
import * as fs from 'node:fs';
import { defineConfig } from 'cypress';
import coverageTask from '@cypress/code-coverage/task';

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
    numTestsKeptInMemory: process.env.CI ? 1 : 5,
    setupNodeEvents: (on, config) => {
      on('after:spec', (spec: Cypress.Spec, results: CypressCommandLine.RunResult) => {
        if (results && results.video) {
          // Do we have failures for any retry attempts?
          const failures = results.tests.some(test => test.attempts.some(attempt => attempt.state === 'failed'));
          if (!failures) {
            // delete the video if the spec passed and no tests retried
            fs.unlinkSync(results.video);
          }
        }
      });
      return coverageTask(on, config);
    },
  },
  defaultCommandTimeout: 60000,
  responseTimeout: 60000,
  pageLoadTimeout: 300000,
});
