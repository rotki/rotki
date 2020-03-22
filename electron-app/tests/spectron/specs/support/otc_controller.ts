import { SpectronClient } from 'spectron';
import { METHOD_TIMEOUT } from '../utils/common';

const retry = require('promise-retry');

export interface OtcTrade {
  [key: string]: string | number;

  readonly otc_timestamp: string;
  readonly otc_pair: string;
  readonly otc_rate: number;
  readonly otc_fee: number;
  readonly otc_fee_currency: string;
  readonly otc_amount: number;
}

export default class OtcController {
  constructor(private client: SpectronClient) {}

  async addTrade(data: OtcTrade) {
    const client = this.client;
    for (const key in data) {
      if (data[key] === null || data[key] === undefined) {
        continue;
      }

      const datum = data[key];
      await retry(async function() {
        await client.addValue(`#${key}`, datum);
      });
    }

    await retry(async function() {
      await client.click('#otctradesubmit');
    });

    await this.closeSuccessDialog();
  }

  async closeSuccessDialog() {
    const client = this.client;
    await client.waitUntilTextExists(
      '.jconfirm-title',
      'Success',
      METHOD_TIMEOUT
    );

    await retry(async () => {
      await client.click('.jconfirm-buttons>button');
    });

    await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);
  }
}

export const otcData: OtcTrade[] = [
  {
    otc_timestamp: '08/10/2015 10:48:55',
    otc_pair: 'BTC_EUR',
    otc_rate: 268.678317859,
    otc_fee: 0,
    otc_fee_currency: 'BTC',
    otc_amount: 82
  },
  {
    otc_timestamp: '08/10/2015 10:48:55',
    otc_pair: 'ETH_EUR',
    otc_rate: 0.2315893,
    otc_fee: 0,
    otc_fee_currency: 'ETH',
    otc_amount: 1450
  }
];
