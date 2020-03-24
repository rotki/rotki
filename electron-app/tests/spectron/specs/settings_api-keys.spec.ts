import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT,
  navigateTo,
  selectFromUserMenu,
  setupTest
} from './utils/common';
import { Guid } from '../../common/guid';
import { ApiKeysController } from './support/api-keys-controller';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('API Keys', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  let controller: ApiKeysController;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);
    await setupTest(application, 'api keys', async () => {
      await createAccount(application, username, password);

      controller = new ApiKeysController(client);

      await navigateTo(client, '.navigation__api-keys');
      await client.waitForVisible('.api-keys', METHOD_TIMEOUT);
      // navigate to accounting settings and then back to api keys to
      // try and recreate https://github.com/rotki/rotki/issues/320
      await selectFromUserMenu(client, '.user-dropdown__accounting-settings');
      await client.waitUntilTextExists(
        '.page-header',
        'Accounting Settings',
        METHOD_TIMEOUT
      );
      await navigateTo(client, '.navigation__api-keys');
      await client.waitForVisible('.api-keys', METHOD_TIMEOUT);
    });
  });

  afterAll(async () => {
    await stop();
  });

  afterEach(async () => {
    await captureOnFailure(application);
  });

  test('add an exchange key and and verify that it was added', async () => {
    const apiKey = process.env.BITTREX_API_KEY as string;
    const apiSecret = process.env.BITTREX_API_SECRET as string;

    await controller.addExchange(apiKey, apiSecret);

    await client.scroll('.exchange-settings', 0, 0);

    client.click('.exchange-settings__fields__exchange');

    await client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
    client.element(`.v-list-item__title=bittrex`).click();

    await client.waitForVisible('.v-select-list', METHOD_TIMEOUT, false);

    await client.waitForEnabled(
      '.exchange-settings__fields__api-key input',
      METHOD_TIMEOUT,
      true
    );
    await expect(
      client.element('.exchange-settings__fields__api-key input').isEnabled()
    ).resolves.toBe(false);
    await expect(
      client.element('.exchange-settings__fields__api-secret input').isEnabled()
    ).resolves.toBe(false);
  });
});
