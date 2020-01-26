import { SpectronClient } from 'spectron';
import { METHOD_TIMEOUT } from '../utils/common';
const retry = require('promise-retry');

export class ApiKeysController {
  constructor(private client: SpectronClient) {}

  async addExchange(apiKey: string, apiSecret: string) {
    await this.client.scroll('.exchange-settings', 0, 0);
    await retry(async () => {
      this.client.click('.exchange-settings__fields__exchange');
    });

    await this.client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
    this.client.element(`.v-list-item__title=bittrex`).click();
    await this.client.waitForVisible('.v-select-list', METHOD_TIMEOUT, false);

    await this.client.scroll('.exchange-settings__fields__api-key', 0, 0);
    await this.client.addValue(
      '.exchange-settings__fields__api-key input',
      apiKey
    );
    await this.client.scroll('.exchange-settings__fields__api-secret', 0, 0);
    await this.client.addValue(
      '.exchange-settings__fields__api-secret input',
      apiSecret
    );

    this.client.click('.exchange-settings__buttons__setup');
    await this.client.waitForExist('#bittrex_badge', METHOD_TIMEOUT);
  }
}
