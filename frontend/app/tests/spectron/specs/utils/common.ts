import * as fs from 'fs';
import { Application, SpectronClient } from 'spectron';

const retry = require('promise-retry');

export const GLOBAL_TIMEOUT = 120_000;
const METHOD_TIMEOUT = 40_000;

const opts = { timeout: METHOD_TIMEOUT };

async function wait(ms: number) {
  if (ms === undefined) ms = 1000;

  return new Promise(function (resolve) {
    setTimeout(resolve, ms);
  });
}

export async function createAccount(
  app: Application,
  username: string,
  password: string
) {
  const { client } = app;
  const { $ } = client;
  const uname = await $('.login__fields__username');
  await uname.waitForDisplayed(opts);

  (await $('.login__button__new-account')).click();

  await (await $('.create-account')).waitForExist(opts);
  await wait(1000);

  (await $('.create-account__fields__username')).click();

  (await $('.create-account__fields__username input')).addValue(username);

  await wait(200);
  (await $('.create-account__fields__password')).click();
  (await $('.create-account__fields__password input')).addValue(password);
  await wait(200);
  (await $('.create-account__fields__password-repeat')).click();
  (await $('.create-account__fields__password-repeat input')).addValue(
    password
  );

  (await $('.create-account__buttons__confirm')).click();

  await client.waitUntilTextExists('div', `Upgrade to Premium`, METHOD_TIMEOUT);
  (await $('.message-overlay__buttons__cancel')).click();
}

async function selectFromUserMenu(client: SpectronClient, elementId: string) {
  const { $ } = client;
  const dropdown = await $('.user-dropdown');
  await dropdown.waitForDisplayed(opts);
  await dropdown.click();
  const element = await $(elementId);
  await element.waitForDisplayed(opts);
  await element.click();
  await dropdown.waitForDisplayed({ ...opts, reverse: true });
  await client.pause(500);
}

export async function logout(client: SpectronClient) {
  const { $ } = client;
  await selectFromUserMenu(client, '.user-dropdown__logout');

  (await $('.confirm-dialog__body')).waitForDisplayed(opts);
  const confirm = await $('.confirm-dialog__buttons__confirm');
  await retry(async () => {
    await confirm.click();
  });
  (await $('.login__fields__username')).waitForDisplayed(opts);
}

function takeScreenshot(app: Application, title: string): Promise<void> {
  const filename = getScreenshotFilename(title);
  return new Promise<void>((resolve, reject) => {
    app.browserWindow.capturePage().then(imageBuffer => {
      fs.writeFile(filename, imageBuffer.getNativeHandle(), (err: any) => {
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

export async function captureOnFailure(app: Application) {
  // @ts-ignore
  const currentTest = window.currentTest;
  if (currentTest && currentTest.failedExpectations.length > 0) {
    await takeScreenshot(app, currentTest.fullName);
  }
}
