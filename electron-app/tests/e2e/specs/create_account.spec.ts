import { Application } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT
} from './utils/common';
import { Guid } from './utils/guid';

jest.setTimeout(GLOBAL_TIMEOUT);
jest.retryTimes(3);

describe('first usage', () => {
  let app: Application;
  let stop: () => Promise<Application>;

  beforeEach(async () => {
    const testEnvironment = await initSpectron();
    app = testEnvironment.application;
    stop = testEnvironment.stop;
  });

  afterEach(async function() {
    await captureOnFailure(app);
    await stop();
  });

  it('create account', async () => {
    const username: string = Guid.newGuid().toString();
    const password: string = process.env.PASSWORD as string;

    await createAccount(app, username, password);

    await app.client.waitForVisible('.user-dropdown', METHOD_TIMEOUT);
    await app.client.click('.user-dropdown');
    await app.client.waitForVisible('.user-dropdown__logout', METHOD_TIMEOUT);
    await app.client.click('.user-dropdown__logout');
    await app.client.waitForVisible('.confirm-dialog', METHOD_TIMEOUT);
    await app.client.click('.confirm-dialog__buttons__confirm');
    await app.client.waitForVisible('.login', METHOD_TIMEOUT);
  });
});
