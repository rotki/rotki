import {ActionResult, UnlockResult} from './model/action-result';
import {AssetBalance} from './model/asset-balance';
import {DBAssetBalance} from './model/db-asset-balance';
import {SingleAssetBalance} from './model/single-asset-balance';
import {BlockchainAccountResult} from './model/blockchain_account_result';
import {OtcTrade} from './model/otc-trade';
import {IgnoredAssetsResponse} from './model/ignored_assets_response';
import {Currency} from './model/currency';
import {LocationData} from './model/location-data';
import {AsyncQueryResult} from './model/balance-result';
import {EthTokensResult} from './model/eth_tokens_result';
import {PeriodicClientQueryResult} from './model/periodic_client_query_result';
import {NetvalueDataResult} from './model/query-netvalue-data-result';
import {Messages} from './model/messages';
import {VersionCheck} from './model/version-check';

const zerorpc = require('zerorpc-rotkehlchen');
// max timeout is now 9999 seconds
const client = new zerorpc.Client({timeout: 9999, heartbeatInterval: 15000});


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

    logout(): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke('logout', (error: Error) => {
                if (error) {
                    reject(error);
                } else {
                    resolve(true);
                }
            });
        });
    }

    query_periodic_data(): Promise<PeriodicClientQueryResult> {
        return new Promise<PeriodicClientQueryResult>((resolve, reject) => {
            client.invoke('query_periodic_data', (error: Error, res: PeriodicClientQueryResult) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(res);
                }
            });
        });
    }

    set_premium_credentials(api_key: string, api_secret: string): Promise<boolean> {
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

    delete_otctrade(id: number): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke('delete_otctrade', id, (error: Error, res: ActionResult<boolean>) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    if (!res.result) {
                        reject(new Error(res.message));
                    } else {
                        resolve(true);
                    }
                }
            });
        });
    }

    query_otctrades(): Promise<OtcTrade[]> {
        return new Promise<OtcTrade[]>((resolve, reject) => {
            client.invoke('query_otctrades', (error: Error, result: ActionResult<OtcTrade[]>) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(result.result);
                    }
                }
            });
        });
    }

    get_ignored_assets(): Promise<string[]> {
        return new Promise<string[]>((resolve, reject) => {
            client.invoke('get_ignored_assets', (error: Error, result: IgnoredAssetsResponse) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result.ignored_assets);
                }
            });
        });
    }

    version_check(): Promise<VersionCheck> {
        return new Promise<VersionCheck>((resolve, reject) => {
            client.invoke('version_check', (error: Error, result: VersionCheck) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    set_settings(settings: { [key: string]: any }): Promise<ActionResult<boolean>> {
        return new Promise<ActionResult<boolean>>((resolve, reject) => {
            client.invoke('set_settings', settings, (error: Error, result: ActionResult<boolean>) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else if (!result.result) {
                    reject(new Error(result.message));
                } else {
                    resolve(result);
                }
            });
        });
    }

    set_main_currency(currency: Currency): Promise<ActionResult<boolean>> {
        return new Promise<ActionResult<boolean>>((resolve, reject) => {
            client.invoke('set_main_currency', currency.ticker_symbol, (error: Error, result: ActionResult<boolean>) => {
                if (error) {
                    reject(error);
                } else if (!result.result) {
                    reject(new Error(result.message));
                } else {
                    resolve(result);
                }
            });
        });
    }

    query_exchange_balances_async(name: string): Promise<AsyncQueryResult> {
        return new Promise<AsyncQueryResult>((resolve, reject) => {
            client.invoke('query_exchange_balances_async', name, (error: Error, result: AsyncQueryResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    query_balances_async(): Promise<AsyncQueryResult> {
        return new Promise<AsyncQueryResult>((resolve, reject) => {
            client.invoke('query_balances_async', (error: Error, result: AsyncQueryResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    query_blockchain_balances_async(): Promise<AsyncQueryResult> {
        return new Promise<AsyncQueryResult>((resolve, reject) => {
            client.invoke('query_blockchain_balances_async', (error: Error, result: AsyncQueryResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    query_fiat_balances(): Promise<{ [currency: string]: AssetBalance }> {
        return new Promise<{ [p: string]: AssetBalance }>((resolve, reject) => {
            client.invoke('query_fiat_balances', (error: Error, res: { [currency: string]: AssetBalance }) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(res);
                }
            });
        });
    }

    query_task_result(id: number): Promise<any> {
        return new Promise<boolean>(resolve => {
            client.invoke('query_task_result', id, (_error: Error, res: any) => {
                resolve(res);
            });
        });
    }

    query_netvalue_data(): Promise<NetvalueDataResult> {
        return new Promise<NetvalueDataResult>((resolve, reject) => {
            client.invoke('query_netvalue_data', (error: Error, result: NetvalueDataResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    query_owned_assets(): Promise<string[]> {
        return new Promise<string[]>((resolve, reject) => {
            client.invoke('query_owned_assets', (error: Error, res: ActionResult<string[]>) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(res.result);
                }
            });
        });
    }

    query_timed_balances_data(asset: string, start_ts: number, end_ts: number): Promise<SingleAssetBalance[]> {
        return new Promise<SingleAssetBalance[]>((resolve, reject) => {
            client.invoke(
                'query_timed_balances_data',
                asset,
                start_ts,
                end_ts,
                (error: Error, res: ActionResult<SingleAssetBalance[]>) => {
                    if (error || res == null) {
                        reject(error || new NoResponseError());
                    } else {
                        resolve(res.result);
                    }
                });
        });
    }

    query_latest_location_value_distribution(): Promise<LocationData[]> {
        return new Promise<LocationData[]>((resolve, reject) => {
            client.invoke(
                'query_latest_location_value_distribution',
                (error: Error, res: ActionResult<LocationData[]>) => {
                    if (error || res == null) {
                        reject(error || new NoResponseError());
                    } else {
                        resolve(res.result);
                    }
                });
        });
    }

    query_latest_asset_value_distribution(): Promise<DBAssetBalance[]> {
        return new Promise<DBAssetBalance[]>((resolve, reject) => {
            client.invoke(
                'query_latest_asset_value_distribution',
                (error: Error, res: ActionResult<DBAssetBalance[]>) => {
                    if (error || res == null) {
                        reject(error || new NoResponseError());
                    } else {
                        resolve(res.result);
                    }
                });
        });
    }

    query_statistics_renderer(): Promise<string> {
        return new Promise<string>((resolve, reject) => {
            client.invoke('query_statistics_renderer', (error: Error, res: ActionResult<string>) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    if (!res.result) {
                        reject(new Error(res.message));
                    } else {
                        resolve(res.result);
                    }
                }
            });
        });
    }

    process_trade_history_async(start_ts: number, end_ts: number): Promise<AsyncQueryResult> {
        return new Promise<AsyncQueryResult>((resolve, reject) => {
            client.invoke('process_trade_history_async', start_ts, end_ts, (error: Error, result: AsyncQueryResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    set_premium_option_sync(should_sync: boolean): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke('set_premium_option_sync', should_sync, (error: Error, res: boolean) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(true);
                }
            });
        });
    }

    get_fiat_exchange_rates(): Promise<{ exchange_rates: { [currency: string]: string } }> {
        return new Promise<{ exchange_rates: { [p: string]: string } }>((resolve, reject) => {
            client.invoke('get_fiat_exchange_rates', [], (error: Error, res: { exchange_rates: { [currency: string]: string } }) => {
                if (error || res == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(res);
                }
            });
        });
    }

    unlock_user(
        username: string,
        password: string,
        create_true: boolean,
        sync_approval: string,
        api_key: string,
        api_secret: string
    ): Promise<UnlockResult> {
        return new Promise<UnlockResult>((resolve, reject) => {
            client.invoke(
                'unlock_user',
                username,
                password,
                create_true,
                sync_approval,
                api_key,
                api_secret,
                (error: Error, res: UnlockResult) => {
                    if (error || res == null) {
                        reject(error || new NoResponseError());
                    } else {
                        resolve(res);
                    }
                });
        });
    }

    remove_exchange(exchange_name: string): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke(
                'remove_exchange',
                exchange_name,
                (error: Error, res: ActionResult<boolean>) => {
                    if (error || res == null) {
                        reject(error || new NoResponseError());
                    } else if (!res.result) {
                        reject(new Error(res.message));
                    } else {
                        resolve(true);
                    }
                });
        });
    }

    get_eth_tokens(): Promise<EthTokensResult> {
        return new Promise<EthTokensResult>((resolve, reject) => {
            client.invoke('get_eth_tokens', (error: Error, result: EthTokensResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else {
                    resolve(result);
                }
            });
        });
    }

    import_data_from(source: string, filepath: string): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke(
                'import_data_from',
                source,
                filepath,
                (error: Error, result: ActionResult<boolean>) => {
                    if (error || result == null) {
                        reject(error || new NoResponseError());
                    } else if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(true);
                    }
                });
        });
    }

    remove_blockchain_account(blockchain: string, account: string): Promise<BlockchainAccountResult> {
        return new Promise<BlockchainAccountResult>((resolve, reject) => {
            client.invoke('remove_blockchain_account', blockchain, account, (error: Error, result: BlockchainAccountResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else if (!result.result) {
                    reject(new Error(result.message));
                } else {
                    resolve(result);
                }
            });
        });
    }

    add_blockchain_account(blockchain: string, account: string): Promise<BlockchainAccountResult> {
        return new Promise<BlockchainAccountResult>((resolve, reject) => {
            client.invoke('add_blockchain_account', blockchain, account, (error: Error, result: BlockchainAccountResult) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else if (!result.result) {
                    reject(new Error(result.message));
                } else {
                    resolve(result);
                }
            });
        });
    }

    set_fiat_balance(currency: string, balance: string): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke(
                'set_fiat_balance',
                currency,
                balance,
                (error: Error, result: ActionResult<boolean>) => {
                    if (error || result == null) {
                        reject(error || new NoResponseError());
                    } else if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(true);
                    }
                });
        });
    }

    setup_exchange(exchange_name: string, api_key: string, api_secret: string): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke(
                'setup_exchange',
                exchange_name,
                api_key,
                api_secret,
                (error: Error, result: ActionResult<boolean>) => {
                    if (error || result == null) {
                        reject(error || new NoResponseError());
                    } else if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(true);
                    }
                });
        });
    }

    export_processed_history_csv(directory: string): Promise<boolean> {
        return new Promise<boolean>((resolve, reject) => {
            client.invoke('export_processed_history_csv', directory, (error: Error, result: ActionResult<boolean>) => {
                if (error || result == null) {
                    reject(error || new NoResponseError());
                } else if (!result.result) {
                    reject(new Error(result.message));
                } else {
                    resolve(true);
                }
            });
        });
    }

    modify_asset(add: boolean, asset: string): Promise<boolean> {
        let command: string;
        if (add) {
            command = 'add_ignored_asset';
        } else {
            command = 'remove_ignored_asset';
        }

        return new Promise<boolean>((resolve, reject) => {
            client.invoke(
                command,
                asset,
                (error: Error, result: ActionResult<boolean>) => {
                    if (error || result == null) {
                        reject(error || new NoResponseError());
                    } else if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(true);
                    }
                });
        });
    }

    modify_otc_trades(add: boolean, payload: { [key: string]: any }): Promise<boolean> {
        let command: string;
        if (add) {
            command = 'add_otctrade';
        } else {
            command = 'edit_otctrade';
        }
        return new Promise<boolean>((resolve, reject) => {
            client.invoke(
                command,
                payload,
                (error: Error, result: ActionResult<boolean>) => {
                    if (error || result == null) {
                        reject(error || new NoResponseError());
                    } else if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(true);
                    }
                });
        });
    }

    consumeMessages(): Promise<Messages> {
        return new Promise<any>((resolve, reject) => {
            client.invoke(
                'consume_messages',
                (error: Error, result: ActionResult<Messages>) => {
                    if (error || result == null) {
                        reject(error || new NoResponseError());
                    } else if (!result.result) {
                        reject(new Error(result.message));
                    } else {
                        resolve(result.result);
                    }
                }
            );
        });
    }
}

export const service = new RotkehlchenService();
