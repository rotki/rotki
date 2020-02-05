import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  logout
} from './utils/common';
import { Guid } from './utils/guid';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('on first usage', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  const username: string = Guid.newGuid().toString();
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    ({ application, stop } = await initSpectron());
    ({ client } = application);
  });

  afterEach(async () => {
    await captureOnFailure(application);
  });

  afterAll(async () => {
    await stop();
  });

  test('create a new account', async () => {
    await createAccount(application, username, password);
  });

  test('logout', async () => {
    await logout(client);
  });
});
