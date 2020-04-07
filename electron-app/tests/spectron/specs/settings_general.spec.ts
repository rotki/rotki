import { Application, SpectronClient } from 'spectron';
import { Guid } from '../../common/guid';
import {
  captureOnFailure,
  clearValue,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  login,
  logout,
  METHOD_TIMEOUT,
  selectFromUserMenu,
  setupTest
} from './utils/common';

const retry = require('promise-retry');

jest.setTimeout(GLOBAL_TIMEOUT);

async function changeValue(
  client: SpectronClient,
  elementSelector: string,
  expectedValue: string
) {
  await client.waitUntil(
    async () => await client.element(elementSelector).isEnabled(),
    METHOD_TIMEOUT
  );

  await clearValue(client, elementSelector);

  await retry(async () => {
    await client.addValue(elementSelector, expectedValue);
  });

  await expect(client.getValue(elementSelector)).resolves.toEqual(
    expectedValue
  );
}

async function verifyDialog(
  client: SpectronClient,
  title: string,
  message: string
) {
  await client.waitForVisible('.message-dialog__title', METHOD_TIMEOUT);
  await expect(
    client.element('.message-dialog__title').getText()
  ).resolves.toMatch(title);
  await expect(
    client.element('.message-dialog__message').getText()
  ).resolves.toMatch(message);

  await client.click('.message-dialog__buttons__confirm');
  await client.waitForVisible('.message-dialog__message', METHOD_TIMEOUT, true);
  await expect(
    client.element('.message-dialog__message').isVisible()
  ).resolves.toBe(false);
}

describe('general settings', () => {
  let application: Application;
  let client: SpectronClient;
  let stop: () => Promise<Application>;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);
    await setupTest(application, 'general settings', async () => {
      await createAccount(application, username, password);
      await selectFromUserMenu(client, '.user-dropdown__settings');
      await client.waitUntilTextExists('h1', 'Settings', METHOD_TIMEOUT);
    });
  });

  afterAll(async () => {
    await stop();
  });

  afterEach(async () => {
    await captureOnFailure(application);
  });

  describe('change settings one by one and verify that they change', () => {
    test('floating precision', async () => {
      await changeValue(
        client,
        '.settings-general__fields__floating-precision input',
        '4'
      );
    });

    test('anonymized logs', async () => {
      await client.click('.settings-general__fields__anonymized-logs label');
      await expect(
        client.getAttribute(
          '.settings-general__fields__anonymized-logs input',
          'aria-checked'
        )
      ).resolves.toBe('true');
    });

    test('anonymous usage statistic', async () => {
      await client.click(
        '.settings-general__fields__anonymous-usage-statistics label'
      );
      await expect(
        client.getAttribute(
          '.settings-general__fields__anonymous-usage-statistics input',
          'aria-checked'
        )
      ).resolves.toBe('false');
    });

    test('historic data start', async () => {
      await changeValue(
        client,
        '.settings-general__fields__historic-data-start input',
        '03/10/2018'
      );
    });

    test('currency selection', async () => {
      await client.waitUntil(
        () =>
          client
            .element('.settings-general__fields__currency-selector')
            .isEnabled(),
        METHOD_TIMEOUT
      );
      await client
        .element('.settings-general__fields__currency-selector')
        .click();
      await client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
      await client.element(`.v-list-item__title=JPY`).click();
      await client.waitForVisible('.v-select-list', METHOD_TIMEOUT, true);

      await expect(
        client.getText(
          '.settings-general__fields__currency-selector .v-select__selection'
        )
      ).resolves.toMatch('JPY');
    });

    test('balance save frequency', async () => {
      await changeValue(
        client,
        '.settings-general__fields__balance-save-frequency input',
        '48'
      );
    });

    test('date display format', async () => {
      await changeValue(
        client,
        '.settings-general__fields__date-display-format input',
        '%d-%m-%Y %H:%M:%S %z'
      );
    });
  });

  test('save settings and confirm saving', async () => {
    await retry(async () => {
      client.click('.settings-general__buttons__save');
    });

    await verifyDialog(client, 'Success', 'Successfully changed settings.');
  });

  test('change rpc without success', async () => {
    await changeValue(
      client,
      '.settings-general__fields__rpc-endpoint input',
      'http://localhost:9001'
    );

    await retry(async () => {
      client.click('.settings-general__buttons__save');
    });

    await verifyDialog(
      client,
      'Error',
      'Error at changing settings: Failed to connect to ethereum node at endpoint http://localhost:9001'
    );

    await expect(
      client.getValue('.settings-general__fields__rpc-endpoint input')
    ).resolves.toEqual('http://localhost:8545');
  });

  describe('verify that changes persist after login in', () => {
    beforeAll(async () => {
      try {
        await logout(client);
        await login(client, username, password);

        await client.waitUntilTextExists('h1', 'Dashboard', METHOD_TIMEOUT);

        await selectFromUserMenu(client, '.user-dropdown__settings');

        await client.waitUntilTextExists('h1', 'Settings', METHOD_TIMEOUT);
      } catch (e) {
        await captureOnFailure(application);
        throw e;
      }
    });

    test('floating precision', async () => {
      await expect(
        client.getValue('.settings-general__fields__floating-precision input')
      ).resolves.toEqual('4');
    });

    test('anonymized logs', async () => {
      await expect(
        client.getAttribute(
          '.settings-general__fields__anonymized-logs input',
          'aria-checked'
        )
      ).resolves.toBe('true');
    });

    test('anonymous usage statistics', async () => {
      await expect(
        client.getAttribute(
          '.settings-general__fields__anonymous-usage-statistics input',
          'aria-checked'
        )
      ).resolves.toBe('false');
    });

    test('historic data start', async () => {
      await expect(
        client.getValue('.settings-general__fields__historic-data-start input')
      ).resolves.toEqual('03/10/2018');
    });

    test('main currency', async () => {
      await expect(
        client.getText(
          '.settings-general__fields__currency-selector .v-select__selection'
        )
      ).resolves.toMatch('JPY');
    });

    test('rpc endpoint', async () => {
      await expect(
        client.getValue('.settings-general__fields__rpc-endpoint input')
      ).resolves.toEqual('http://localhost:8545');
    });

    test('balance save frequency', async () => {
      await expect(
        client.getValue(
          '.settings-general__fields__balance-save-frequency input'
        )
      ).resolves.toEqual('48');
    });

    test('date display format', async () => {
      await expect(
        client.getValue('.settings-general__fields__date-display-format input')
      ).resolves.toEqual('%d-%m-%Y %H:%M:%S %z');
    });
  });
});
