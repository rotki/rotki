import { ActionResult } from './model/action-result';
import { AssetBalance } from './model/asset-balance';
import { BlockchainAccountResult } from './model/blockchain_account_result';
import { showError } from './utils';

const zerorpc = require('zerorpc');
// max timeout is now 9999 seconds
export const client = new zerorpc.Client({timeout: 9999, heartbeatInterval: 15000});


export class NoResponseError extends Error {
    constructor() {
        super('No response received from rpc');
    }
}

export class NoPremiumCredentials extends Error {
}

export class RotkehlchenService {

    connect(): void {
        client.connect('tcp://127.0.0.1:4242');
    }

    queryLastBalanceSaveTime(): Promise<number> {

        return new Promise<number>((resolve, reject) => {
            // for now only query when was the last time balance data was saved
            client.invoke('query_last_balance_save_time', (error: Error, res: number) => {
                if (error || res == null) {
                    console.log('Error at periodic client query');
                    reject(error || new NoResponseError());
                } else {
                    resolve(res);
                }
            });
        });
    }

    setPremiumCredentials(api_key: string, api_secret: string): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke('set_premium_credentials', api_key, api_secret, (error: Error, res: ActionResult<boolean>) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                    return;
                }
                if (!res.result) {
                    reject(new NoPremiumCredentials(res.message));
                    return;
                }
                resolve(res.result);
            });
        });
    }

    query_fiat_balances(): Promise<{ [currency: string]: AssetBalance }> {
        return new Promise<{ [currency: string]: AssetBalance }>((resolve, reject) => {
            client.invoke('query_fiat_balances', (error: Error, result: { [currency: string]: AssetBalance }) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                    return;
                }

                resolve(result);
            });
        });
    }

    remove_owned_eth_tokens(tokens: string[]): Promise<BlockchainAccountResult> {
        return new Promise<BlockchainAccountResult>((resolve, reject) => {
            client.invoke('remove_owned_eth_tokens', tokens, (error: Error, result: BlockchainAccountResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                    return;
                }
                if (!result.result) {
                    reject(new Error(result.message));
                    return;
                }
                resolve(result);
            });
        });

    }

    add_owned_eth_tokens(tokens: string[]): Promise<BlockchainAccountResult> {
        return new Promise<BlockchainAccountResult>((resolve, reject) => {
            client.invoke('add_owned_eth_tokens', tokens, (error: Error, result: BlockchainAccountResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                    return;
                }
                if (!result.result) {
                    reject(new Error(result.message));
                    return;
                }
                resolve(result);
            });
        });
    }

}

export const service = new RotkehlchenService();
