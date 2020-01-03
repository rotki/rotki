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

describe('first usage', () => {
  let application: Application;
  let stop: () => Promise<Application>;

  beforeEach(async () => {
    ({ application, stop } = await initSpectron());
  });

  afterEach(async () => {
    await captureOnFailure(application);
    await stop();
  });

  it('create account', async () => {
    const username: string = Guid.newGuid().toString();
    const password: string = process.env.PASSWORD as string;

    await createAccount(application, username, password);

    const { client } = application;

    await client.waitForVisible('.user-dropdown', METHOD_TIMEOUT);
    await client.click('.user-dropdown');
    await client.waitForVisible('.user-dropdown__logout', METHOD_TIMEOUT);
    await client.click('.user-dropdown__logout');
    await client.waitForVisible('.confirm-dialog', METHOD_TIMEOUT);
    await client.click('.confirm-dialog__buttons__confirm');
    await client.waitForVisible('.login', METHOD_TIMEOUT);
  });
});
