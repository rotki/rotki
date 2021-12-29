import { Blockchain } from '@rotki/common/lib/blockchain';
import { ActionResult } from '@rotki/common/lib/data';
import {
  Eth2DailyStats,
  Eth2DailyStatsPayload
} from '@rotki/common/lib/staking/eth2';
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { SupportedCurrency } from '@/data/currencies';
import { AssetApi } from '@/services/assets/asset-api';
import {
  axiosNoRootCamelCaseTransformer,
  axiosSnakeCaseTransformer,
  getUpdatedKey,
  setupTransformer
} from '@/services/axios-tranformers';
import { BackupApi } from '@/services/backup/backup-api';
import { BalancesApi } from '@/services/balances/balances-api';
import { basicAxiosTransformer } from '@/services/consts';
import { DefiApi } from '@/services/defi/defi-api';
import { IgnoredActions } from '@/services/history/const';
import { HistoryApi } from '@/services/history/history-api';
import { ReportsApi } from '@/services/reports/reports-api';
import { SessionApi } from '@/services/session/session-api';
import {
  AsyncQuery,
  BackendInfo,
  BtcAccountData,
  DBAssetBalance,
  GeneralAccountData,
  LocationData,
  Messages,
  NetValue,
  PendingTask,
  PeriodicClientQueryResult,
  SingleAssetBalance,
  SyncAction,
  TaskNotFoundError,
  TaskStatus
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
  AllBalancePayload,
  BlockchainAccountPayload,
  ExchangePayload,
  XpubPayload
} from '@/store/balances/types';
import { IgnoreActionType } from '@/store/history/types';
import { SyncConflictPayload } from '@/store/session/types';
import { ActionStatus } from '@/store/types';
import { Exchange, Exchanges } from '@/types/exchanges';
import {
  AccountSession,
  CreateAccountPayload,
  LoginCredentials,
  SyncConflictError
} from '@/types/login';
import { TaskResultResponse } from '@/types/task';
import {
  ExternalServiceKey,
  ExternalServiceKeys,
  ExternalServiceName,
  SettingsUpdate,
  Tag,
  Tags,
  UserAccount,
  UserSettingsModel
} from '@/types/user';
import { assert } from '@/utils/assertions';
import { nonNullProperties } from '@/utils/data';

export class RotkehlchenApi {
  private axios: AxiosInstance;
  private _defi: DefiApi;
  private _session: SessionApi;
  private _balances: BalancesApi;
  private _history: HistoryApi;
  private _reports: ReportsApi;
  private _assets: AssetApi;
  private _backups: BackupApi;
  private _serverUrl: string;
  private readonly baseTransformer = setupTransformer([]);

  get serverUrl(): string {
    return this._serverUrl;
  }

  get defaultBackend(): boolean {
    return this._serverUrl === process.env.VUE_APP_BACKEND_URL;
  }

  private setupApis = (axios: AxiosInstance) => ({
    defi: new DefiApi(axios),
    session: new SessionApi(axios),
    balances: new BalancesApi(axios),
    history: new HistoryApi(axios),
    reports: new ReportsApi(axios),
    assets: new AssetApi(axios),
    backups: new BackupApi(axios)
  });

  constructor() {
    this._serverUrl = process.env.VUE_APP_BACKEND_URL!;
    this.axios = axios.create({
      baseURL: `${this.serverUrl}/api/1/`,
      timeout: 30000
    });
    this.baseTransformer = setupTransformer();
    ({
      defi: this._defi,
      session: this._session,
      balances: this._balances,
      history: this._history,
      reports: this._reports,
      assets: this._assets,
      backups: this._backups
    } = this.setupApis(this.axios));
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

  get reports(): ReportsApi {
    return this._reports;
  }

  get assets(): AssetApi {
    return this._assets;
  }

  get backups(): BackupApi {
    return this._backups;
  }

  setup(serverUrl: string) {
    this._serverUrl = serverUrl;
    this.axios = axios.create({
      baseURL: `${serverUrl}/api/1/`,
      timeout: 30000
    });
    ({
      defi: this._defi,
      session: this._session,
      balances: this._balances,
      history: this._history,
      reports: this._reports,
      assets: this._assets,
      backups: this._backups
    } = this.setupApis(this.axios));
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

  async users(): Promise<string[]> {
    const response = await this.axios.get<ActionResult<AccountSession>>(
      `/users`
    );
    const data = handleResponse(response);
    return Object.keys(data);
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
      .then(value => {
        if (value.status === 409) {
          return true;
        }
        return handleResponse(value);
      });
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

  async setSettings(settings: SettingsUpdate): Promise<UserSettingsModel> {
    const response = await this.axios.put<ActionResult<UserSettingsModel>>(
      '/settings',
      axiosSnakeCaseTransformer({
        settings: settings
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
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

  queryBalancesAsync(payload: Partial<AllBalancePayload>): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/balances/', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ...payload
        }),
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
      .get<ActionResult<TaskResultResponse<ActionResult<T>>>>(`/tasks/${id}`, {
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

  queryNetvalueData(includeNfts: boolean): Promise<NetValue> {
    return this.axios
      .get<ActionResult<NetValue>>('/statistics/netvalue', {
        params: axiosSnakeCaseTransformer({
          includeNfts
        }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  queryTimedBalancesData(
    asset: string,
    startTs: number,
    endTs: number
  ): Promise<SingleAssetBalance[]> {
    return this.axios
      .get<ActionResult<SingleAssetBalance[]>>(`/statistics/balance/${asset}`, {
        params: {
          from_timestamp: startTs,
          to_timestamp: endTs
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

  async createAccount(payload: CreateAccountPayload): Promise<UserAccount> {
    const { credentials, premiumSetup } = payload;
    const { username, password } = credentials;

    const response = await this.axios.put<ActionResult<UserAccount>>(
      '/users',
      axiosSnakeCaseTransformer({
        name: username,
        password,
        premiumApiKey: premiumSetup?.apiKey,
        premiumApiSecret: premiumSetup?.apiSecret,
        initialSettings: {
          submitUsageAnalytics: premiumSetup?.submitUsageAnalytics
        },
        syncDatabase: premiumSetup?.syncDatabase
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    const account = handleResponse(response);
    return UserAccount.parse(account);
  }

  async login(credentials: LoginCredentials): Promise<UserAccount> {
    const { password, syncApproval, username } = credentials;
    const response = await this.axios.patch<
      ActionResult<UserAccount | SyncConflictPayload>
    >(
      `/users/${username}`,
      axiosSnakeCaseTransformer({
        action: 'login',
        password,
        syncApproval
      }),
      {
        validateStatus: validAccountOperationStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    if (response.status === 300) {
      const { result, message } = response.data;
      throw new SyncConflictError(message, SyncConflictPayload.parse(result));
    }

    const account = handleResponse(response);
    return UserAccount.parse(account);
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

  importDataFrom(
    source: string,
    file: string,
    timestampFormat: string | null
  ): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/import',
        axiosSnakeCaseTransformer({
          source,
          file,
          timestampFormat
        }),
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
    assert(blockchain !== Blockchain.BTC, 'call editBtcAccount for btc');
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

  async getSettings(): Promise<UserSettingsModel> {
    const response = await this.axios.get<ActionResult<UserSettingsModel>>(
      '/settings',
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return UserSettingsModel.parse(data);
  }

  async getExchanges(): Promise<Exchanges> {
    const response = await this.axios.get<ActionResult<Exchanges>>(
      '/exchanges',
      {
        transformResponse: basicAxiosTransformer,
        validateStatus: validWithSessionStatus
      }
    );

    const data = handleResponse(response);
    return Exchanges.parse(data);
  }

  async queryExternalServices(): Promise<ExternalServiceKeys> {
    const response = await this.axios.get<ActionResult<ExternalServiceKeys>>(
      '/external_services/',
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  }

  async setExternalServices(
    keys: ExternalServiceKey[]
  ): Promise<ExternalServiceKeys> {
    const response = await this.axios.put<ActionResult<ExternalServiceKeys>>(
      '/external_services/',
      axiosSnakeCaseTransformer({
        services: keys
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  }

  async deleteExternalServices(
    serviceToDelete: ExternalServiceName
  ): Promise<ExternalServiceKeys> {
    const response = await this.axios.delete<ActionResult<ExternalServiceKeys>>(
      '/external_services/',
      {
        data: {
          services: [serviceToDelete]
        },
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    const data = handleResponse(response);
    return ExternalServiceKeys.parse(data);
  }

  async getTags(): Promise<Tags> {
    const response = await this.axios.get<ActionResult<Tags>>('/tags', {
      validateStatus: validWithSessionStatus
    });

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  }

  async addTag(tag: Tag): Promise<Tags> {
    const response = await this.axios.put<ActionResult<Tags>>(
      '/tags',
      axiosSnakeCaseTransformer(tag),
      {
        validateStatus: validStatus
      }
    );

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  }

  async editTag(tag: Tag): Promise<Tags> {
    const response = await this.axios.patch<ActionResult<Tags>>(
      '/tags',
      axiosSnakeCaseTransformer(tag),
      {
        validateStatus: validStatus
      }
    );

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  }

  async deleteTag(tagName: string): Promise<Tags> {
    const response = await this.axios.delete<ActionResult<Tags>>('/tags', {
      data: {
        name: tagName
      },
      validateStatus: validStatus
    });

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  }

  async accounts(
    blockchain: Exclude<Blockchain, Blockchain.BTC | Blockchain.ETH2>
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
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/blockchains/ETH2/stake/details',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async eth2StakingDeposits(): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/blockchains/ETH2/stake/deposits',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  private async internalEth2Stats<T>(
    payload: any,
    asyncQuery: boolean
  ): Promise<T> {
    const response = await this.axios.post<ActionResult<T>>(
      '/blockchains/ETH2/stake/dailystats',
      axiosSnakeCaseTransformer({
        asyncQuery,
        ...payload,
        orderByAttribute: getUpdatedKey(payload.orderByAttribute, false)
      }),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async eth2StatsTask(payload: Eth2DailyStatsPayload): Promise<PendingTask> {
    return this.internalEth2Stats(payload, true);
  }

  async eth2Stats(payload: Eth2DailyStatsPayload): Promise<Eth2DailyStats> {
    const stats = await this.internalEth2Stats<Eth2DailyStats>(payload, false);
    return Eth2DailyStats.parse(stats);
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

  queryBinanceMarkets(location: string): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/exchanges/binance/pairs', {
        params: axiosSnakeCaseTransformer({
          location: location
        })
      })
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
      .get('/history/download/', {
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
  ): Promise<IgnoredActions> {
    return this.axios
      .put<ActionResult<IgnoredActions>>(
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
      .then(handleResponse)
      .then(data => IgnoredActions.parse(data));
  }

  async unignoreActions(
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoredActions> {
    return this.axios
      .delete<ActionResult<IgnoredActions>>('/actions/ignored', {
        data: axiosSnakeCaseTransformer({
          actionIds,
          actionType
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse)
      .then(data => IgnoredActions.parse(data));
  }

  async erc20details(address: string): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH/erc20details/', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          address
        }),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async fetchNfts(payload?: { ignoreCache: boolean }): Promise<PendingTask> {
    const params = Object.assign(
      {
        asyncQuery: true
      },
      payload
    );
    return this.axios
      .get<ActionResult<PendingTask>>('/nfts', {
        params: axiosSnakeCaseTransformer(params),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }
}

export const api = new RotkehlchenApi();
