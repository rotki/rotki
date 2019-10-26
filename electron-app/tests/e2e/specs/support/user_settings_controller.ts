import { SpectronClient } from 'spectron';
import { METHOD_TIMEOUT } from './common';
const retry = require('promise-retry');
export enum AccountType {
  ETH = 'ETH',
  BTC = 'BTC'
}

export class UserSettingsController {
  constructor(private client: SpectronClient) {}

  async addFiatValue(amount: number = 50) {
    await this.client.scroll('#fiat_type_entry', 0, 0);
    await this.client.click('#fiat_type_entry');
    await this.client.element('#fiat_type_entry').click('option=USD');
    await this.client.addValue('#fiat_value_entry', amount);
    await retry(async () => {
      this.client.click('#modify_fiat_button');
    });
  }

  async addAccount(accountType: AccountType, account: string) {
    await this.clearAccountInput();
    await retry(async () => {
      this.client.scroll('#crypto_type_entry', 0, 0);
      this.client.click('#crypto_type_entry');
      this.client.element('#crypto_type_entry').click(`option=${accountType}`);
    });

    await this.client.addValue('#account_entry', account);
    await this.client.click('#add_account_button');
  }

  async clearAccountInput() {
    await this.client.waitForEnabled('#account_entry', METHOD_TIMEOUT);
    await this.client.waitForEnabled('#crypto_type_entry', METHOD_TIMEOUT);
    await this.client.waitForEnabled('#add_account_button', METHOD_TIMEOUT);
    await this.client.clearElement('#account_entry');
  }

  async addExchange(apiKey: string, apiSecret: string) {
    await this.client.scroll('#setup_exchange', 0, 0);
    await retry(async () => {
      this.client.click('#setup_exchange');
    });
    await this.client.element('#setup_exchange').click('option=bittrex');

    await this.client.addValue('#api_key_entry', apiKey);
    await this.client.addValue('#api_secret_entry', apiSecret);

    await retry(async () => {
      this.client.click('#setup_exchange_button');
    });

    await this.client.waitForExist('#bittrex_badge', METHOD_TIMEOUT);
  }
}
