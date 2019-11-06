import { Application, SpectronClient } from 'spectron';
import * as electron from 'electron';
import * as fs from 'fs';
import { spawn } from 'child_process';
const retry = require('promise-retry');

export const GLOBAL_TIMEOUT = 120_000;
export const METHOD_TIMEOUT = 40_000;

type AsyncBlock = () => Promise<void>;

type TestEnvironment = {
  application: Application;
  stop: () => Promise<Application>;
  url: string;
  log: string;
};

export async function initSpectron(): Promise<TestEnvironment> {
  return new Promise(async (resolve, reject) => {
    let log = '';
    let outputDir = '';

    const child = spawn(
      require.resolve('@vue/cli-service/bin/vue-cli-service'),
      ['electron:serve', '--headless', '--mode', 'test'],
      {
        env: {
          ...process.env,
          NODE_ENV: 'production'
        }
      }
    );

    child.on('error', err => {
      reject(err);
    });

    if (!child.stdout) {
      reject(new Error('Undefined stdout'));
      return;
    }

    child.stdout.on('data', async data => {
      data = data.toString();
      log += data;

      const urlMatch = data.match(
        /\$WEBPACK_DEV_SERVER_URL=https?:\/\/[^/]+\//
      );

      const outputDirMatch = data.match(/\$outputDir=\b.*\b/);

      if (outputDirMatch) {
        // Record output dir
        outputDir = outputDirMatch[0].split('=')[1];
      }

      if (urlMatch) {
        const url: string = urlMatch[0].split('=')[1];

        const application = new Application({
          path: (electron as any).default,
          args: [`${outputDir}`],
          chromeDriverArgs: ['--disable-extensions'],
          env: {
            ELECTRON_ENABLE_LOGGING: true,
            ELECTRON_ENABLE_STACK_DUMPING: true,
            NODE_ENV: 'production',
            IS_TEST: true,
            SPECTRON: true
          },
          startTimeout: METHOD_TIMEOUT,
          connectionRetryTimeout: GLOBAL_TIMEOUT,
          waitTimeout: METHOD_TIMEOUT,
          chromeDriverLogPath: '../chromedriverlog.txt'
        });

        await application.start();
        await application.client.waitUntilWindowLoaded(METHOD_TIMEOUT);

        const stop = () => {
          child.stdin!!.write('close');
          child.kill();

          if (application) {
            return application.stop();
          }
          return Promise.resolve(application);
        };

        resolve({ log, url, application, stop });
      }
    });
  });
}

export async function wait(ms: number) {
  if (ms === undefined) ms = 1000;

  return new Promise(function(resolve) {
    setTimeout(resolve, ms);
  });
}

export async function createAccount(
  app: Application,
  username: string,
  password: string
) {
  await app.client.waitForVisible('.login', METHOD_TIMEOUT);

  await app.client.click('.login__button__new-account');
  await app.client.waitForExist('.create-account', METHOD_TIMEOUT);
  await wait(1000);

  await app.client.click('.create-account__fields__username');
  await app.client.addValue(
    '.create-account__fields__username input',
    username
  );

  await wait(200);
  await app.client.click('.create-account__fields__password');
  await app.client.addValue(
    '.create-account__fields__password input',
    password
  );
  await wait(200);
  await app.client.click('.create-account__fields__password-repeat');
  await app.client.addValue(
    '.create-account__fields__password-repeat input',
    password
  );

  await app.client.click('.create-account__buttons__confirm');
  await app.client.waitUntilTextExists(
    'div',
    `Welcome to Rotki!`,
    METHOD_TIMEOUT
  );
  await app.client.click('.message-overlay__buttons__cancel');
  await app.client.waitUntilTextExists(
    'div',
    `Upgrade to Premium`,
    METHOD_TIMEOUT
  );
  await app.client.click('.message-overlay__buttons__cancel');
  await app.client.waitForVisible('.confirm-dialog', METHOD_TIMEOUT, false);
}

export async function navigateTo(client: SpectronClient, elementId: string) {
  await client.click('.user-dropdown');
  await client.waitForVisible(elementId, METHOD_TIMEOUT);
  await client.click(elementId);
  await client.waitForVisible('.user-dropdown', METHOD_TIMEOUT, false);
  await client.pause(500);
}

export async function closeAddYourSettingsPopup(client: SpectronClient) {
  await client.waitUntilTextExists(
    '.jconfirm-title',
    'Add your settings',
    METHOD_TIMEOUT
  );
  await retry(async () => {
    await client.click('.jconfirm-buttons>button');
  });
}

export async function logout(client: SpectronClient) {
  await retry(async () => {
    client.click('#user-dropdown');
  });
  await client.waitForVisible('#logout_button', METHOD_TIMEOUT);
  await retry(async () => {
    client.click('#logout_button');
  });

  await client.waitForVisible('.jconfirm', METHOD_TIMEOUT);
  await retry(async () => {
    client.click('.jconfirm-buttons>button');
  });
  await client.waitUntilTextExists(
    '.jconfirm-title',
    'Sign In',
    METHOD_TIMEOUT
  );
}

export async function login(
  client: SpectronClient,
  username: string,
  password: string
) {
  await client.clearElement('#username_entry');
  await client.addValue('#username_entry', username);

  await client.clearElement('#password_entry');
  await client.addValue('#password_entry', password);

  await retry(async () => {
    client.click('.jconfirm-buttons>button');
  });

  await client.waitUntilTextExists(
    '.jconfirm-title',
    'Successful Sign In',
    METHOD_TIMEOUT
  );
  await retry(async () => {
    client.click('.jconfirm-buttons>button');
  });
  await client.waitForVisible('.jconfirm', METHOD_TIMEOUT, true);
}

export function takeScreenshot(app: Application, title: string): Promise<void> {
  const filename = getScreenshotFilename(title);
  return new Promise<void>((resolve, reject) => {
    app.browserWindow.capturePage().then(imageBuffer => {
      fs.writeFile(filename, imageBuffer, (err: any) => {
        if (err) {
          console.log(err);
          reject(err);
        } else {
          console.log(`Took screenshot: ${title}`);
          resolve();
        }
      });
    });
  });
}

function getScreenshotFilename(title: string) {
  const directory = 'failure-screenshots';
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory);
  }
  return `${directory}/${title.replace(/\s/g, '_')}.png`;
}

export async function setupTest(
  app: Application,
  title: string,
  block: AsyncBlock
): Promise<void> {
  try {
    await block();
  } catch (e) {
    await takeScreenshot(app, title);
    throw e;
  }
}

export async function captureOnFailure(app: Application) {
  // @ts-ignore
  const currentTest = window.currentTest;
  if (currentTest && currentTest.failedExpectations.length > 0) {
    await takeScreenshot(app, currentTest.fullName);
  }
}
