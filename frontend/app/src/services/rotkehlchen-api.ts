import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { SupportedCurrency } from '@/data/currencies';
import {
  AccountState,
  DBSettings,
  Exchange,
  ExternalServiceKeys
} from '@/model/action-result';
import { AssetApi } from '@/services/assets/asset-api';
import {
  axiosCamelCaseTransformer,
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { BalancesApi } from '@/services/balances/balances-api';
import { basicAxiosTransformer } from '@/services/consts';
import { DefiApi } from '@/services/defi/defi-api';
import { HistoryApi } from '@/services/history/history-api';
import { SessionApi } from '@/services/session/session-api';
import {
  ActionResult,
  AsyncQuery,
  BtcAccountData,
  DBAssetBalance,
  GeneralAccountData,
  IgnoreActionResult,
  LocationData,
  Messages,
  NetValue,
  PendingTask,
  PeriodicClientQueryResult,
  SingleAssetBalance,
  SyncAction,
  TaskNotFoundError,
  TaskStatus,
  BackendInfo
} from '@/services/types-api';
import {
  handleResponse,
  validAccountOperationStatus,
  validAuthorizedStatus,
  validStatus,
  validTaskStatus,
  validWithoutSessionStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import {
  AccountPayload,
  BlockchainAccountPayload,
  ExchangePayload,
  XpubPayload
} from '@/store/balances/types';
import { IgnoreActionType } from '@/store/history/types';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import {
  AccountSession,
  Blockchain,
  BTC,
  ExternalServiceKey,
  ExternalServiceName,
  SettingsUpdate,
  SyncApproval,
  SyncConflictError,
  Tag,
  Tags,
  TaskResult,
  UnlockPayload
} from '@/typing/types';
import { assert } from '@/utils/assertions';
import { nonNullProperties } from '@/utils/data';

export class RotkehlchenApi {
  private axios: AxiosInstance;
  private _defi: DefiApi;
  private _session: SessionApi;
  private _balances: BalancesApi;
  private _history: HistoryApi;
  private _assets: AssetApi;
  private _serverUrl: string;
  private readonly baseTransformer = setupTransformer([]);

  get serverUrl(): string {
    return this._serverUrl;
  }

  get defaultBackend(): boolean {
    return this._serverUrl === process.env.VUE_APP_BACKEND_URL;
  }

  constructor() {
    this._serverUrl = process.env.VUE_APP_BACKEND_URL!;
    this.axios = axios.create({
      baseURL: `${this.serverUrl}/api/1/`,
      timeout: 30000
    });
    this.baseTransformer = setupTransformer();
    this._defi = new DefiApi(this.axios);
    this._session = new SessionApi(this.axios);
    this._balances = new BalancesApi(this.axios);
    this._history = new HistoryApi(this.axios);
    this._assets = new AssetApi(this.axios);
  }

  get defi(): DefiApi {
    return this._defi;
  }

  get session(): SessionApi {
    return this._session;
  }

  get balances(): BalancesApi {
    return this._balances;
  }

  get history(): HistoryApi {
    return this._history;
  }

  get assets(): AssetApi {
    return this._assets;
  }

  setup(serverUrl: string) {
    this._serverUrl = serverUrl;
    this.axios = axios.create({
      baseURL: `${serverUrl}/api/1/`,
      timeout: 30000
    });
    this._defi = new DefiApi(this.axios);
    this._session = new SessionApi(this.axios);
    this._balances = new BalancesApi(this.axios);
    this._history = new HistoryApi(this.axios);
    this._assets = new AssetApi(this.axios);
  }

  checkIfLogged(username: string): Promise<boolean> {
    return this.axios
      .get<ActionResult<AccountSession>>(`/users`)
      .then(handleResponse)
      .then(result => result[username] === 'loggedin');
  }

  loggedUsers(): Promise<string[]> {
    return this.axios
      .get<ActionResult<AccountSession>>(`/users`)
      .then(handleResponse)
      .then(result => {
        const loggedUsers: string[] = [];
        for (const user in result) {
          if (result[user] !== 'loggedin') {
            continue;
          }
          loggedUsers.push(user);
        }
        return loggedUsers;
      });
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
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
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

  deletePremiumCredentials(): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/premium', {
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

  async ping(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/ping') // no validate status here since defaults work
      .then(handleResponse);
  }

  info(): Promise<BackendInfo> {
    return this.axios
      .get<ActionResult<BackendInfo>>('/info', {
        transformResponse: basicAxiosTransformer
      })
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

  queryExchangeBalances(
    location: string,
    ignoreCache: boolean = false
  ): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(`/exchanges/balances/${location}`, {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ignoreCache: ignoreCache ? true : undefined
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
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

  queryTasks(): Promise<TaskStatus> {
    return this.axios
      .get<ActionResult<TaskStatus>>(`/tasks/`, {
        validateStatus: validTaskStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  queryTaskResult<T>(
    id: number,
    numericKeys?: string[] | null
  ): Promise<ActionResult<T>> {
    const requiresSetup = numericKeys || numericKeys === null;
    const transformer = requiresSetup
      ? setupTransformer(numericKeys)
      : this.axios.defaults.transformResponse;

    return this.axios
      .get<ActionResult<TaskResult<ActionResult<T>>>>(`/tasks/${id}`, {
        validateStatus: validTaskStatus,
        transformResponse: transformer
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

  queryNetvalueData(): Promise<NetValue> {
    return this.axios
      .get<ActionResult<NetValue>>('/statistics/netvalue', {
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

  processTradeHistoryAsync(start: number, end: number): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/history/', {
        params: {
          async_query: true,
          from_timestamp: start,
          to_timestamp: end
        },
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  getFiatExchangeRates(currencies: SupportedCurrency[]): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/exchange_rates', {
        params: {
          async_query: true,
          currencies: currencies.join(',')
        },
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async unlockUser(payload: UnlockPayload): Promise<AccountState> {
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
    const state: Writeable<AccountState> = await this.login(
      username,
      password,
      syncApproval
    );
    // TODO: Remove after migrating settings logic to use the transformers
    state.exchanges = axiosCamelCaseTransformer(state.exchanges);
    return state;
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
          throw new SyncConflictError(
            response.data.message,
            axiosCamelCaseTransformer(response.data.result)
          );
        }
        return response;
      })
      .then(handleResponse);
  }

  removeExchange({ location, name }: Exchange): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/exchanges', {
        data: {
          name,
          location
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  importDataFrom(source: string, file: string): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/import',
        {
          source,
          file
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  removeBlockchainAccount(
    blockchain: string,
    accounts: string[]
  ): Promise<PendingTask> {
    return this.axios
      .delete<ActionResult<PendingTask>>(`/blockchains/${blockchain}`, {
        data: axiosSnakeCaseTransformer({
          asyncQuery: true,
          accounts: accounts
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  addBlockchainAccount({
    address,
    blockchain,
    label,
    tags,
    xpub
  }: BlockchainAccountPayload): Promise<PendingTask> {
    const url = xpub
      ? `/blockchains/${blockchain}/xpub`
      : `/blockchains/${blockchain}`;

    const basePayload = {
      label,
      tags
    };

    const payload = xpub
      ? {
          xpub: xpub.xpub,
          derivationPath: xpub.derivationPath ? xpub.derivationPath : undefined,
          xpubType: xpub.xpubType ? xpub.xpubType : undefined,
          ...basePayload
        }
      : {
          accounts: [
            {
              address,
              ...basePayload
            }
          ]
        };
    return this.performAsyncQuery(url, payload);
  }

  addBlockchainAccounts(chain: Blockchain, payload: AccountPayload[]) {
    return this.performAsyncQuery(`/blockchains/${chain}`, {
      accounts: payload
    });
  }

  private performAsyncQuery(url: string, payload: any) {
    return this.axios
      .put<ActionResult<PendingTask>>(
        url,
        axiosSnakeCaseTransformer({
          asyncQuery: true,
          ...payload
        }),
        {
          validateStatus: validWithParamsSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async editBtcAccount(
    payload: BlockchainAccountPayload
  ): Promise<BtcAccountData> {
    let url = '/blockchains/BTC';
    const { address, label, tags } = payload;

    let data: {};
    if (payload.xpub && !payload.address) {
      url += '/xpub';
      const { derivationPath, xpub } = payload.xpub;
      data = {
        xpub,
        derivationPath: derivationPath ? derivationPath : undefined,
        label,
        tags
      };
    } else {
      data = {
        accounts: [
          {
            address,
            label,
            tags
          }
        ]
      };
    }

    return this.axios
      .patch<ActionResult<BtcAccountData>>(
        url,
        axiosSnakeCaseTransformer(data),
        {
          validateStatus: validWithParamsSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async editAccount(
    payload: BlockchainAccountPayload
  ): Promise<GeneralAccountData[]> {
    const { address, label, tags, blockchain } = payload;
    assert(blockchain !== BTC, 'call editBtcAccount for btc');
    return this.axios
      .patch<ActionResult<GeneralAccountData[]>>(
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
          validateStatus: validWithParamsSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async deleteXpub({
    derivationPath,
    xpub
  }: XpubPayload): Promise<PendingTask> {
    return this.axios
      .delete<ActionResult<PendingTask>>(`/blockchains/BTC/xpub`, {
        data: axiosSnakeCaseTransformer({
          xpub,
          derivationPath: derivationPath ? derivationPath : undefined,
          asyncQuery: true
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async setupExchange(
    payload: ExchangePayload,
    edit: Boolean
  ): Promise<boolean> {
    let request: Promise<AxiosResponse<ActionResult<boolean>>>;

    if (!edit) {
      request = this.axios.put<ActionResult<boolean>>(
        '/exchanges',
        axiosSnakeCaseTransformer(nonNullProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    } else {
      request = this.axios.patch<ActionResult<boolean>>(
        '/exchanges',
        axiosSnakeCaseTransformer(nonNullProperties(payload)),
        {
          validateStatus: validStatus
        }
      );
    }

    return request.then(handleResponse);
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

  async getExchanges(): Promise<Exchange[]> {
    return this.axios
      .get<ActionResult<Exchange[]>>('/exchanges', {
        transformResponse: this.baseTransformer,
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

  async accounts(
    blockchain: Exclude<Blockchain, 'BTC'>
  ): Promise<GeneralAccountData[]> {
    return this.axios
      .get<ActionResult<GeneralAccountData[]>>(`/blockchains/${blockchain}`, {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async btcAccounts(): Promise<BtcAccountData> {
    return this.axios
      .get<ActionResult<BtcAccountData>>('/blockchains/BTC', {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async forceSync(action: SyncAction): Promise<PendingTask> {
    return this.axios
      .put<ActionResult<PendingTask>>(
        '/premium/sync',
        axiosSnakeCaseTransformer({ asyncQuery: true, action }),
        {
          validateStatus: validWithParamsSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async eth2StakingDetails(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH2/stake/details', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async eth2StakingDeposits(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH2/stake/deposits', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async adexBalances(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        '/blockchains/ETH/modules/adex/balances',
        {
          params: axiosSnakeCaseTransformer({
            asyncQuery: true
          }),
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async adexHistory(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH/modules/adex/history', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  importFile(data: FormData) {
    return this.axios
      .post<ActionResult<boolean>>('/import', data, {
        validateStatus: validStatus,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      .then(handleResponse);
  }

  queryBinanceMarkets(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/exchanges/binance/pairs')
      .then(handleResponse);
  }

  queryBinanceUserMarkets(name: string, location: string): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>(`/exchanges/binance/pairs/${name}`, {
        params: axiosSnakeCaseTransformer({
          location: location
        })
      })
      .then(handleResponse);
  }

  downloadCSV(): Promise<ActionStatus> {
    return this.axios
      .get('/history/download', {
        responseType: 'blob',
        validateStatus: validTaskStatus
      })
      .then(async response => {
        if (response.status === 200) {
          const url = window.URL.createObjectURL(response.data);
          const link = document.createElement('a');
          link.id = 'history-download-link';
          link.href = url;
          link.setAttribute('download', 'reports.zip');
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          return { success: true };
        }

        const body = await (response.data as Blob).text();
        const result: ActionResult<null> = JSON.parse(body);

        return { success: false, message: result.message };
      })
      .catch(reason => {
        return { success: false, message: reason.message };
      });
  }

  async airdrops(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH/airdrops', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async ignoreActions(
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoreActionResult> {
    return this.axios
      .put<ActionResult<IgnoreActionResult>>(
        '/actions/ignored',
        axiosSnakeCaseTransformer({
          actionIds,
          actionType
        }),
        {
          validateStatus: validStatus,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async unignoreActions(
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoreActionResult> {
    return this.axios
      .delete<ActionResult<IgnoreActionResult>>('/actions/ignored', {
        data: axiosSnakeCaseTransformer({
          actionIds,
          actionType
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async erc20details(address: string): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH/erc20details', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          address
        }),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }
}

export const api = new RotkehlchenApi();
