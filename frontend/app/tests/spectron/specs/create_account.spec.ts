import { Application, SpectronClient } from 'spectron';
import * as spectron from 'spectron';
import { testWithSpectron } from 'vue-cli-plugin-electron-builder/index';
import { Guid } from '../../common/guid';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  logout
} from './utils/common';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('on first usage', () => {
  let app: Application;
  let stopServe: () => Promise<Application>;
  let client: SpectronClient;

  const username: string = Guid.newGuid().toString();
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    ({ app, stopServe } = await testWithSpectron(spectron));
    ({ client } = app);
  });

  afterEach(async () => {
    await captureOnFailure(app);
  });

  afterAll(async () => {
    await stopServe();
  });

  test('create a new account', async () => {
    await createAccount(app, username, password);
  });

  test('logout', async () => {
    await logout(client);
  });
});
