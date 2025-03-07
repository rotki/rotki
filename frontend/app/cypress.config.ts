import * as fs from 'node:fs';
import * as process from 'node:process';
import coverageTask from '@cypress/code-coverage/task';
import { defineConfig } from 'cypress';

const group = process.env.GROUP ? `${process.env.GROUP}/` : '';
const captureVideo = !!process.env.CI;

export default defineConfig({
  viewportWidth: 1280,
  viewportHeight: 720,
  e2e: {
    baseUrl: 'http://localhost:22230',
    fixturesFolder: 'tests/e2e/fixtures',
    specPattern: `tests/e2e/specs/${group}**/*.cy.ts`,
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
      on('after:spec', (spec: Cypress.Spec, results?: CypressCommandLine.RunResult) => {
        // When running via cypress open the results are undefined and there is nothing to do.
        if (!results) {
          return;
        }
        // Do we have failures for any retry attempts?
        const failures = results.tests.some(test => test.attempts.some(attempt => attempt.state === 'failed'));

        if (results.video && !failures) {
          // delete the video if the spec passed and no tests retried
          fs.unlinkSync(results.video);
        }

        if (failures) {
          // throwing an exception here seems to properly stop the suite from running.
          // process exit does not seem to work
          throw new Error(`spec: ${spec.name} had failures, bailing out.`);
        }
      });

      return coverageTask(on, config);
    },
  },
  defaultCommandTimeout: 60000,
  responseTimeout: 60000,
  pageLoadTimeout: 300000,
});
