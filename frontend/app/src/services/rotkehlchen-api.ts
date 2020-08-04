import axios, { AxiosInstance } from 'axios';
import {
  AccountState,
  ActionResult,
  ApiAccountData,
  AsyncQuery,
  DBSettings,
  ExternalServiceKeys
} from '@/model/action-result';
import { DBAssetBalance } from '@/model/db-asset-balance';
import { LocationData } from '@/model/location-data';
import { Messages } from '@/model/messages';
import { PeriodicClientQueryResult } from '@/model/periodic_client_query_result';
import { NetvalueDataResult } from '@/model/query-netvalue-data-result';
import { SingleAssetBalance } from '@/model/single-asset-balance';
import { StoredTrade, Trade } from '@/model/stored-trade';
import { VersionCheck } from '@/model/version-check';
import { DefiApi } from '@/services/defi/defi-api';
import { SessionApi } from '@/services/session/session-api';
import {
  ApiManualBalance,
  ApiManualBalances,
  SupportedAssets,
  TaskNotFoundError
} from '@/services/types-api';
import {
  validWithSessionAndExternalService,
  handleResponse,
  validWithParamsSessionAndExternalService,
  validStatus,
  validAccountOperationStatus,
  validWithoutSessionStatus,
  validWithSessionStatus,
  validAuthorizedStatus,
  validTaskStatus
} from '@/services/utils';
import { BlockchainAccountPayload } from '@/store/balances/actions';
import {
  AccountData,
  AccountSession,
  ApiAssetBalances,
  Blockchain,
  ExternalServiceKey,
  ExternalServiceName,
  FiatExchangeRates,
  SettingsUpdate,
  SyncApproval,
  SyncConflictError,
  Tag,
  Tags,
  TaskResult,
  UnlockPayload
} from '@/typing/types';
import { convertAccountData } from '@/utils/conversion';

export class RotkehlchenApi {
  private readonly axios: AxiosInstance;
  readonly defi: DefiApi;
  readonly session: SessionApi;

  constructor() {
    this.axios = axios.create({
      baseURL: `${process.env.VUE_APP_BACKEND_URL}/api/1/`,
      timeout: 30000
    });
    this.defi = new DefiApi(this.axios);
    this.session = new SessionApi(this.axios);
  }

  checkIfLogged(username: string): Promise<boolean> {
    return this.axios
      .get<ActionResult<AccountSession>>(`/users`)
      .then(handleResponse)
      .then(result => result[username] === 'loggedin');
  }

  logout(username: string): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        `/users/${username}`,
        {
          action: 'logout'
        },
        { validateStatus: validAccountOperationStatus }
      )
      .then(handleResponse);
  }

  queryPeriodicData(): Promise<PeriodicClientQueryResult> {
    return this.axios
      .get<ActionResult<PeriodicClientQueryResult>>('/periodic/', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);
  }

  setPremiumCredentials(
    username: string,
    apiKey: string,
    apiSecret: string
  ): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        `/users/${username}`,
        {
          premium_api_key: apiKey,
          premium_api_secret: apiSecret
        },
        { validateStatus: validAuthorizedStatus }
      )
      .then(handleResponse);
  }

  deletePremiumCredentials(username: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/users/${username}/premium`, {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  changeUserPassword(
    username: string,
    currentPassword: string,
    newPassword: string
  ): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        `/users/${username}/password`,
        {
          name: username,
          current_password: currentPassword,
          new_password: newPassword
        },
        {
          validateStatus: validAuthorizedStatus
        }
      )
      .then(handleResponse);
  }

  deleteExternalTrade(id: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/trades', {
        data: {
          trade_id: id
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryExternalTrades(): Promise<StoredTrade[]> {
    return this.axios
      .get<ActionResult<StoredTrade[]>>('/trades', {
        params: { location: 'external' },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  ignoredAssets(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/assets/ignored', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async ping(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/ping') // no validate status here since defaults work
      .then(handleResponse);
  }

  checkVersion(): Promise<VersionCheck> {
    return this.axios
      .get<ActionResult<VersionCheck>>('/version')
      .then(handleResponse);
  }
  setSettings(settings: SettingsUpdate): Promise<DBSettings> {
    return this.axios
      .put<ActionResult<DBSettings>>(
        '/settings',
        {
          settings: settings
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  queryExchangeBalancesAsync(
    name: string,
    ignoreCache: boolean = false
  ): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>(`/exchanges/balances/${name}`, {
        params: {
          async_query: true,
          ignore_cache: ignoreCache ? true : undefined
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryBalancesAsync(
    ignoreCache: boolean = false,
    saveData: boolean = false
  ): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/balances/', {
        params: {
          async_query: true,
          ignore_cache: ignoreCache ? true : undefined,
          save_data: saveData ? true : undefined
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryBlockchainBalancesAsync(
    ignoreCache: boolean = false,
    blockchain?: Blockchain
  ): Promise<AsyncQuery> {
    let url = '/balances/blockchains';
    if (blockchain) {
      url += `/${blockchain}`;
    }
    return this.axios
      .get<ActionResult<AsyncQuery>>(url, {
        params: {
          async_query: true,
          ignore_cache: ignoreCache ? true : undefined
        },
        validateStatus: validWithParamsSessionAndExternalService
      })
      .then(handleResponse);
  }

  queryFiatBalances(): Promise<ApiAssetBalances> {
    return this.axios
      .get<ActionResult<ApiAssetBalances>>('/balances/fiat', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryTaskResult<T>(id: number): Promise<ActionResult<T>> {
    return this.axios
      .get<ActionResult<TaskResult<ActionResult<T>>>>(`/tasks/${id}`, {
        validateStatus: validTaskStatus
      })
      .then(response => {
        if (response.status === 404) {
          throw new TaskNotFoundError(`Task with id ${id} not found`);
        }
        return response;
      })
      .then(handleResponse)
      .then(value => {
        if (value.outcome) {
          return value.outcome;
        }
        throw new Error('No result');
      });
  }

  queryNetvalueData(): Promise<NetvalueDataResult> {
    return this.axios
      .get<ActionResult<NetvalueDataResult>>('/statistics/netvalue', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryOwnedAssets(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/assets', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryTimedBalancesData(
    asset: string,
    start_ts: number,
    end_ts: number
  ): Promise<SingleAssetBalance[]> {
    return this.axios
      .get<ActionResult<SingleAssetBalance[]>>(`/statistics/balance/${asset}`, {
        params: {
          from_timestamp: start_ts,
          to_timestamp: end_ts
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryLatestLocationValueDistribution(): Promise<LocationData[]> {
    return this.axios
      .get<ActionResult<LocationData[]>>('/statistics/value_distribution', {
        params: { distribution_by: 'location' },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryLatestAssetValueDistribution(): Promise<DBAssetBalance[]> {
    return this.axios
      .get<ActionResult<DBAssetBalance[]>>('/statistics/value_distribution', {
        params: { distribution_by: 'asset' },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryStatisticsRenderer(): Promise<string> {
    return this.axios
      .get<ActionResult<string>>('/statistics/renderer', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  processTradeHistoryAsync(
    start_ts: number,
    end_ts: number
  ): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/history', {
        params: {
          async_query: true,
          from_timestamp: start_ts,
          to_timestamp: end_ts
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  getFiatExchangeRates(currencies: string[]): Promise<FiatExchangeRates> {
    return this.axios
      .get<ActionResult<FiatExchangeRates>>('/fiat_exchange_rates', {
        params: {
          currencies: currencies.join(',')
        },
        validateStatus: validWithoutSessionStatus
      })
      .then(handleResponse);
  }

  unlockUser(payload: UnlockPayload): Promise<AccountState> {
    const {
      create,
      username,
      password,
      apiKey,
      apiSecret,
      syncApproval,
      submitUsageAnalytics
    } = payload;
    if (create) {
      return this.registerUser(
        username,
        password,
        apiKey,
        apiSecret,
        submitUsageAnalytics !== undefined
          ? { submit_usage_analytics: submitUsageAnalytics }
          : undefined
      );
    }
    return this.login(username, password, syncApproval);
  }

  registerUser(
    name: string,
    password: string,
    apiKey?: string,
    apiSecret?: string,
    initialSettings?: SettingsUpdate
  ): Promise<AccountState> {
    return this.axios
      .put<ActionResult<AccountState>>(
        '/users',
        {
          name,
          password,
          premium_api_key: apiKey,
          premium_api_secret: apiSecret,
          initial_settings: initialSettings
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  login(
    name: string,
    password: string,
    syncApproval: SyncApproval = 'unknown'
  ): Promise<AccountState> {
    return this.axios
      .patch<ActionResult<AccountState>>(
        `/users/${name}`,
        {
          action: 'login',
          password,
          sync_approval: syncApproval
        },
        { validateStatus: validAccountOperationStatus }
      )
      .then(response => {
        if (response.status === 300) {
          throw new SyncConflictError(response.data.message);
        }
        return response;
      })
      .then(handleResponse);
  }

  removeExchange(name: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/exchanges', {
        data: {
          name
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  importDataFrom(source: string, filepath: string): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/import',
        {
          source,
          filepath
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  removeBlockchainAccount(
    blockchain: string,
    account: string
  ): Promise<AsyncQuery> {
    return this.axios
      .delete<ActionResult<AsyncQuery>>(`/blockchains/${blockchain}`, {
        data: {
          async_query: true,
          accounts: [account]
        },
        validateStatus: validWithParamsSessionAndExternalService
      })
      .then(handleResponse);
  }

  addBlockchainAccount(payload: BlockchainAccountPayload): Promise<AsyncQuery> {
    const { blockchain, address, label, tags } = payload;
    return this.axios
      .put<ActionResult<AsyncQuery>>(
        `/blockchains/${blockchain}`,
        {
          async_query: true,
          accounts: [
            {
              address,
              label,
              tags
            }
          ]
        },
        {
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);
  }

  async editBlockchainAccount(
    payload: BlockchainAccountPayload
  ): Promise<AccountData[]> {
    const { blockchain, address, label, tags } = payload;
    return this.axios
      .patch<ActionResult<ApiAccountData[]>>(
        `/blockchains/${blockchain}`,
        {
          accounts: [
            {
              address,
              label,
              tags
            }
          ]
        },
        {
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse)
      .then(accounts => accounts.map(convertAccountData));
  }

  setFiatBalance(currency: string, balance: string): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        '/balances/fiat',
        {
          balances: {
            [currency]: balance
          }
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  setupExchange(
    name: string,
    api_key: string,
    api_secret: string,
    passphrase: string | null
  ): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/exchanges',
        {
          name,
          api_key,
          api_secret,
          passphrase
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  exportHistoryCSV(directory: string): Promise<boolean> {
    return this.axios
      .get<ActionResult<boolean>>('/history/export/', {
        params: {
          directory_path: directory
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  modifyAsset(add: boolean, asset: string): Promise<string[]> {
    if (add) {
      return this.addIgnoredAsset(asset);
    }
    return this.removeIgnoredAsset(asset);
  }

  addIgnoredAsset(asset: string): Promise<string[]> {
    return this.axios
      .put<ActionResult<string[]>>(
        '/assets/ignored',
        {
          assets: [asset]
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  removeIgnoredAsset(asset: string): Promise<string[]> {
    return this.axios
      .delete<ActionResult<string[]>>('/assets/ignored', {
        data: {
          assets: [asset]
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  addExternalTrade(trade: Trade): Promise<StoredTrade[]> {
    return this.axios
      .put<ActionResult<StoredTrade[]>>(
        '/trades',
        {
          ...trade
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  editExternalTrade(trade: StoredTrade): Promise<StoredTrade[]> {
    return this.axios
      .patch<ActionResult<StoredTrade[]>>(
        '/trades',
        {
          ...trade
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  consumeMessages(): Promise<Messages> {
    return this.axios
      .get<ActionResult<Messages>>('/messages/')
      .then(handleResponse);
  }

  async getSettings(): Promise<DBSettings> {
    return this.axios
      .get<ActionResult<DBSettings>>('/settings', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);
  }

  async getExchanges(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/exchanges', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);
  }

  queryExternalServices(): Promise<ExternalServiceKeys> {
    return this.axios
      .get<ActionResult<ExternalServiceKeys>>('/external_services/', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);
  }

  async setExternalServices(
    keys: ExternalServiceKey[]
  ): Promise<ExternalServiceKeys> {
    return this.axios
      .put<ActionResult<ExternalServiceKeys>>(
        '/external_services/',
        {
          services: keys
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  async deleteExternalServices(
    serviceToDelete: ExternalServiceName
  ): Promise<ExternalServiceKeys> {
    return this.axios
      .delete<ActionResult<ExternalServiceKeys>>('/external_services/', {
        data: {
          services: [serviceToDelete]
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async getTags(): Promise<Tags> {
    return this.axios
      .get<ActionResult<Tags>>('/tags', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);
  }

  async addTag(tag: Tag): Promise<Tags> {
    return this.axios
      .put<ActionResult<Tags>>(
        '/tags',
        { ...tag },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  async editTag(tag: Tag): Promise<Tags> {
    return this.axios
      .patch<ActionResult<Tags>>(
        '/tags',
        { ...tag },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  async deleteTag(tagName: string): Promise<Tags> {
    return this.axios
      .delete<ActionResult<Tags>>('/tags', {
        data: {
          name: tagName
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async accounts(blockchain: Blockchain): Promise<AccountData[]> {
    return this.axios
      .get<ActionResult<ApiAccountData[]>>(`/blockchains/${blockchain}`, {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse)
      .then(accounts => accounts.map(convertAccountData));
  }

  async supportedAssets(): Promise<SupportedAssets> {
    return this.axios
      .get<ActionResult<SupportedAssets>>('assets/all', {
        validateStatus: validWithSessionAndExternalService
      })
      .then(handleResponse);
  }

  async manualBalances(): Promise<ApiManualBalances> {
    return this.axios
      .get<ActionResult<ApiManualBalances>>('balances/manual', {
        validateStatus: validWithSessionAndExternalService
      })
      .then(handleResponse);
  }

  async addManualBalances(
    balances: ApiManualBalance[]
  ): Promise<ApiManualBalances> {
    return this.axios
      .put<ActionResult<ApiManualBalances>>(
        'balances/manual',
        {
          balances
        },
        {
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);
  }

  async editManualBalances(
    balances: ApiManualBalance[]
  ): Promise<ApiManualBalances> {
    return this.axios
      .patch<ActionResult<ApiManualBalances>>(
        'balances/manual',
        {
          balances
        },
        {
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);
  }

  async deleteManualBalances(labels: string[]): Promise<ApiManualBalances> {
    return this.axios
      .delete<ActionResult<ApiManualBalances>>('balances/manual', {
        data: { labels },
        validateStatus: validWithParamsSessionAndExternalService
      })
      .then(handleResponse);
  }
}

export const api = new RotkehlchenApi();
