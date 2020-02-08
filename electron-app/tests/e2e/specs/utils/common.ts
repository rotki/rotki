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
  // eslint-disable-next-line no-async-promise-executor
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
  const { client } = app;
  await client.waitForVisible('.login__fields__username', METHOD_TIMEOUT);

  await client.click('.login__button__new-account');
  await client.waitForExist('.create-account', METHOD_TIMEOUT);
  await wait(1000);

  await client.click('.create-account__fields__username');
  await client.addValue('.create-account__fields__username input', username);

  await wait(200);
  await client.click('.create-account__fields__password');
  await client.addValue('.create-account__fields__password input', password);
  await wait(200);
  await client.click('.create-account__fields__password-repeat');
  await client.addValue(
    '.create-account__fields__password-repeat input',
    password
  );

  await client.click('.create-account__buttons__confirm');
  await client.waitUntilTextExists('div', `Upgrade to Premium`, METHOD_TIMEOUT);
  await client.click('.message-overlay__buttons__cancel');
}

export async function selectFromUserMenu(
  client: SpectronClient,
  elementId: string
) {
  await client.waitForVisible('.user-dropdown', METHOD_TIMEOUT);
  await client.click('.user-dropdown');
  await client.waitForVisible(elementId, METHOD_TIMEOUT);
  await client.click(elementId);
  await client.waitForVisible('.user-dropdown', METHOD_TIMEOUT, false);
  await client.pause(500);
}

export async function logout(client: SpectronClient) {
  await selectFromUserMenu(client, '.user-dropdown__logout');

  await client.waitForVisible('.confirm-dialog__body', METHOD_TIMEOUT);
  await retry(async () => {
    await client.click('.confirm-dialog__buttons__confirm');
  });
  await client.waitForVisible('.login__fields__username', METHOD_TIMEOUT);
}

export async function login(
  client: SpectronClient,
  username: string,
  password: string
) {
  await client.waitUntil(
    async () =>
      await client.element('.login__fields__username input').isEnabled()
  );
  await client.addValue('.login__fields__username input', username);
  await client.addValue('.login__fields__password input', password);

  await retry(async () => {
    client.click('.login__button__sign-in');
  });

  await client.waitUntilTextExists('div', `Upgrade to Premium`, METHOD_TIMEOUT);
  await client.click('.message-overlay__buttons__cancel');
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

export async function clearValue(
  client: SpectronClient,
  elementSelector: string
) {
  client.execute((selector: string) => {
    const element: HTMLInputElement = document.querySelector(
      selector
    ) as HTMLInputElement;
    const event: Event = new Event('input', { bubbles: true });
    element.value = '';
    element.dispatchEvent(event);
    element.focus();
  }, elementSelector);
}

export async function navigateTo(client: SpectronClient, selector: string) {
  if (!(await client.isExisting('.v-navigation-drawer--open'))) {
    await client.click('.v-app-bar__nav-icon');
    await client.waitForVisible('.v-navigation-drawer--open', METHOD_TIMEOUT);
  }

  await client.element(selector).click();

  if (await client.isExisting('.v-navigation-drawer--open')) {
    await client.click('.v-app-bar__nav-icon');
    await client.waitForVisible(
      '.v-navigation-drawer--open',
      METHOD_TIMEOUT,
      false
    );
  }
}

export async function dismissSuccessDialog(
  client: SpectronClient,
  message: string
) {
  await client.waitForVisible('.message-dialog__title', METHOD_TIMEOUT);

  await expect(
    client.element('.message-dialog__message').getText()
  ).resolves.toMatch(message);

  await client.click('.message-dialog__buttons__confirm');
  await client.waitForVisible('.message-dialog__title', METHOD_TIMEOUT, true);
}

export async function setValue(
  client: SpectronClient,
  selector: string,
  value: string
) {
  await clearValue(client, selector);
  await client.setValue(selector, value);
  await expect(client.getValue(selector)).resolves.toBe(value);
}

export async function selectOption(
  client: SpectronClient,
  selector: string,
  value: string
) {
  const inputSelector = `${selector}[value='${value}']`;

  const label = client
    .element(inputSelector)
    .$('..')
    .$('..')
    .$('label');
  await label.click();

  await expect(
    client.getAttribute(inputSelector, 'aria-checked')
  ).resolves.toBe('true');
}
