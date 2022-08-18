import { Blockchain } from '@rotki/common/lib/blockchain';
import { ActionResult } from '@rotki/common/lib/data';
import {
  Eth2DailyStats,
  Eth2DailyStatsPayload
} from '@rotki/common/lib/staking/eth2';
import {
  LocationData,
  NetValue,
  TimedAssetBalances,
  TimedBalances
} from '@rotki/common/lib/statistics';
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
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
import {
  BackendConfiguration,
  BackendInfo,
  BtcAccountData,
  GeneralAccountData,
  Messages,
  PendingTask,
  PeriodicClientQueryResult,
  SyncAction,
  TaskNotFoundError,
  TaskStatus
} from '@/services/types-api';
import {
  handleResponse,
  paramsSerializer,
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
  Snapshot,
  SnapshotPayload,
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
import { EthereumRpcNode, EthereumRpcNodeList } from '@/types/settings';
import {
  emptyPagination,
  KrakenStakingEvents,
  KrakenStakingPagination
} from '@/types/staking';
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
import { downloadFileByUrl } from '@/utils/download';

export class RotkehlchenApi {
  private axios: AxiosInstance;
  private _defi: DefiApi;
  private _balances: BalancesApi;
  private _history: HistoryApi;
  private _reports: ReportsApi;
  private _assets: AssetApi;
  private _backups: BackupApi;
  private _serverUrl: string;
  private signal = axios.CancelToken.source();
  private readonly pathname: string;

  get defaultServerUrl(): string {
    if (import.meta.env.VITE_BACKEND_URL) {
      return import.meta.env.VITE_BACKEND_URL as string;
    }

    if (import.meta.env.VITE_PUBLIC_PATH) {
      const pathname = this.pathname;
      return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
    }

    return '';
  }

  get instance(): AxiosInstance {
    return this.axios;
  }

  get serverUrl(): string {
    return this._serverUrl;
  }

  get defaultBackend(): boolean {
    return this._serverUrl === this.defaultServerUrl;
  }

  private cancel() {
    this.signal.cancel('cancelling all pending requests');
    this.signal = axios.CancelToken.source();
  }

  private setupApis = (axios: AxiosInstance) => ({
    defi: new DefiApi(axios),
    balances: new BalancesApi(axios),
    history: new HistoryApi(axios),
    reports: new ReportsApi(axios),
    assets: new AssetApi(axios),
    backups: new BackupApi(axios)
  });

  constructor() {
    this.pathname = window.location.pathname;
    this._serverUrl = this.defaultServerUrl;
    this.axios = axios.create({
      baseURL: `${this.serverUrl}/api/1/`,
      timeout: 30000
    });
    this.setupCancellation();
    ({
      defi: this._defi,
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
    this.setupCancellation();
    ({
      defi: this._defi,
      balances: this._balances,
      history: this._history,
      reports: this._reports,
      assets: this._assets,
      backups: this._backups
    } = this.setupApis(this.axios));
  }

  private setupCancellation() {
    this.axios.interceptors.request.use(
      request => {
        request.cancelToken = this.signal.token;
        return request;
      },
      error => {
        if (error.response) {
          return Promise.reject(error.response.data);
        }
        return Promise.reject(error);
      }
    );
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

  async logout(username: string): Promise<boolean> {
    const response = await this.axios.patch<ActionResult<boolean>>(
      `/users/${username}`,
      {
        action: 'logout'
      },
      { validateStatus: validAccountOperationStatus }
    );

    const success = response.status === 409 ? true : handleResponse(response);
    this.cancel();
    return success;
  }

  async queryPeriodicData(): Promise<PeriodicClientQueryResult> {
    const response = await this.axios.get<
      ActionResult<PeriodicClientQueryResult>
    >('/periodic/', {
      validateStatus: validWithSessionStatus,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  }

  async setPremiumCredentials(
    username: string,
    apiKey: string,
    apiSecret: string
  ): Promise<true> {
    const response = await this.axios.patch<ActionResult<true>>(
      `/users/${username}`,
      {
        premium_api_key: apiKey,
        premium_api_secret: apiSecret
      },
      { validateStatus: validAuthorizedStatus }
    );

    return handleResponse(response);
  }

  async deletePremiumCredentials(): Promise<true> {
    const response = await this.axios.delete<ActionResult<true>>('/premium', {
      validateStatus: validStatus
    });

    return handleResponse(response);
  }

  async changeUserPassword(
    username: string,
    currentPassword: string,
    newPassword: string
  ): Promise<true> {
    const response = await this.axios.patch<ActionResult<true>>(
      `/users/${username}/password`,
      {
        name: username,
        current_password: currentPassword,
        new_password: newPassword
      },
      {
        validateStatus: validAuthorizedStatus
      }
    );

    return handleResponse(response);
  }

  async ping(): Promise<PendingTask> {
    const ping = await this.axios.get<ActionResult<PendingTask>>('/ping', {
      transformResponse: basicAxiosTransformer
    }); // no validate status here since defaults work
    return handleResponse(ping);
  }

  async info(checkForUpdates: boolean = false): Promise<BackendInfo> {
    const response = await this.axios.get<ActionResult<BackendInfo>>('/info', {
      params: axiosSnakeCaseTransformer({
        checkForUpdates
      }),
      transformResponse: basicAxiosTransformer
    });
    return BackendInfo.parse(handleResponse(response));
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

  async queryExchangeBalances(
    location: string,
    ignoreCache: boolean = false
  ): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      `/exchanges/balances/${location}`,
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ignoreCache: ignoreCache ? true : undefined
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async queryBalancesAsync(
    payload: Partial<AllBalancePayload>
  ): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/balances/',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ...payload
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async queryTasks(): Promise<TaskStatus> {
    const response = await this.axios.get<ActionResult<TaskStatus>>(`/tasks/`, {
      validateStatus: validTaskStatus,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  }

  queryTaskResult<T>(
    id: number,
    numericKeys?: string[] | null,
    transform: boolean = true
  ): Promise<ActionResult<T>> {
    const requiresSetup = numericKeys || numericKeys === null;
    const transformer = requiresSetup
      ? setupTransformer(numericKeys)
      : this.axios.defaults.transformResponse;

    const config: Partial<AxiosRequestConfig> = {
      validateStatus: validTaskStatus
    };

    if (transform) {
      config.transformResponse = transformer;
    }

    return this.axios
      .get<ActionResult<TaskResultResponse<ActionResult<T>>>>(
        `/tasks/${id}`,
        config
      )
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

  async queryNetvalueData(includeNfts: boolean): Promise<NetValue> {
    const response = await this.axios.get<ActionResult<NetValue>>(
      '/statistics/netvalue',
      {
        params: axiosSnakeCaseTransformer({
          includeNfts
        }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  }

  async queryTimedBalancesData(
    asset: string,
    fromTimestamp: number,
    toTimestamp: number
  ): Promise<TimedBalances> {
    const balances = await this.axios.get<ActionResult<TimedBalances>>(
      `/statistics/balance/${asset}`,
      {
        params: axiosSnakeCaseTransformer({
          fromTimestamp,
          toTimestamp
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return TimedBalances.parse(handleResponse(balances));
  }

  async queryLatestLocationValueDistribution(): Promise<LocationData> {
    const statistics = await this.axios.get<ActionResult<LocationData>>(
      '/statistics/value_distribution',
      {
        params: axiosSnakeCaseTransformer({ distributionBy: 'location' }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return LocationData.parse(handleResponse(statistics));
  }

  async queryLatestAssetValueDistribution(): Promise<TimedAssetBalances> {
    const statistics = await this.axios.get<ActionResult<TimedAssetBalances>>(
      '/statistics/value_distribution',
      {
        params: axiosSnakeCaseTransformer({ distributionBy: 'asset' }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return TimedAssetBalances.parse(handleResponse(statistics));
  }

  async queryStatisticsRenderer(): Promise<string> {
    const response = await this.axios.get<ActionResult<string>>(
      '/statistics/renderer',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  }

  async getFiatExchangeRates(
    currencies: SupportedCurrency[]
  ): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/exchange_rates',
      {
        params: {
          async_query: true,
          currencies
        },
        paramsSerializer,
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
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
    const response = await this.axios.post<
      ActionResult<UserAccount | SyncConflictPayload>
    >(
      `/users/${username}`,
      axiosSnakeCaseTransformer({
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

  async removeExchange({ location, name }: Exchange): Promise<boolean> {
    const response = await this.axios.delete<ActionResult<boolean>>(
      '/exchanges',
      {
        data: {
          name,
          location
        },
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  }

  async importDataFrom(
    source: string,
    file: string,
    timestampFormat: string | null
  ): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/import',
      axiosSnakeCaseTransformer({
        source,
        file,
        timestampFormat,
        asyncQuery: true
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async removeBlockchainAccount(
    blockchain: string,
    accounts: string[]
  ): Promise<PendingTask> {
    const response = await this.axios.delete<ActionResult<PendingTask>>(
      `/blockchains/${blockchain}`,
      {
        data: axiosSnakeCaseTransformer({
          asyncQuery: true,
          accounts: accounts
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
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
      label: label || null,
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

  private async performAsyncQuery(url: string, payload: any) {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      url,
      axiosSnakeCaseTransformer({
        asyncQuery: true,
        ...payload
      }),
      {
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async editBtcAccount(
    payload: BlockchainAccountPayload
  ): Promise<BtcAccountData> {
    let url = `/blockchains/${payload.blockchain}`;
    const { address, label, tags } = payload;

    let data: {};
    if (payload.xpub && !payload.address) {
      url += '/xpub';
      const { derivationPath, xpub } = payload.xpub;
      data = {
        xpub,
        derivationPath: derivationPath ? derivationPath : undefined,
        label: label || null,
        tags
      };
    } else {
      data = {
        accounts: [
          {
            address,
            label: label || null,
            tags
          }
        ]
      };
    }

    const response = await this.axios.patch<ActionResult<BtcAccountData>>(
      url,
      axiosSnakeCaseTransformer(data),
      {
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async editAccount(
    payload: BlockchainAccountPayload
  ): Promise<GeneralAccountData[]> {
    const { address, label, tags, blockchain } = payload;
    assert(
      ![Blockchain.BTC, Blockchain.BCH].includes(blockchain),
      'call editBtcAccount for btc'
    );
    const response = await this.axios.patch<ActionResult<GeneralAccountData[]>>(
      `/blockchains/${blockchain}`,
      {
        accounts: [
          {
            address,
            label: label || null,
            tags
          }
        ]
      },
      {
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async deleteXpub({
    blockchain,
    derivationPath,
    xpub
  }: XpubPayload): Promise<PendingTask> {
    const response = await this.axios.delete<ActionResult<PendingTask>>(
      `/blockchains/${blockchain}/xpub`,
      {
        data: axiosSnakeCaseTransformer({
          xpub,
          derivationPath: derivationPath ? derivationPath : undefined,
          asyncQuery: true
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
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

  async exportHistoryCSV(directory: string): Promise<boolean> {
    const response = await this.axios.get<ActionResult<boolean>>(
      '/history/export/',
      {
        params: {
          directory_path: directory
        },
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  }

  async consumeMessages(): Promise<Messages> {
    const response = await this.axios.get<ActionResult<Messages>>('/messages/');

    return handleResponse(response);
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
    const response = await this.axios.get<ActionResult<GeneralAccountData[]>>(
      `/blockchains/${blockchain}`,
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async btcAccounts(
    blockchain: Blockchain.BTC | Blockchain.BCH
  ): Promise<BtcAccountData> {
    const response = await this.axios.get<ActionResult<BtcAccountData>>(
      `/blockchains/${blockchain}`,
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async forceSync(action: SyncAction): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/premium/sync',
      axiosSnakeCaseTransformer({ asyncQuery: true, action }),
      {
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async importBalancesSnapshot(
    balancesSnapshotFile: string,
    locationDataSnapshotFile: string
  ): Promise<boolean> {
    const response = await this.axios.put<ActionResult<boolean>>(
      '/snapshots',
      axiosSnakeCaseTransformer({
        balancesSnapshotFile,
        locationDataSnapshotFile
      }),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async uploadBalancesSnapshot(
    balancesSnapshotFile: File,
    locationDataSnapshotFile: File
  ): Promise<boolean> {
    const data = new FormData();
    data.append('balances_snapshot_file', balancesSnapshotFile);
    data.append('location_data_snapshot_file', locationDataSnapshotFile);
    const response = await this.axios.post<ActionResult<boolean>>(
      '/snapshots',
      data,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return handleResponse(response);
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
        orderByAttributes:
          payload.orderByAttributes?.map((item: string) =>
            getUpdatedKey(item, false)
          ) ?? []
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
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/blockchains/ETH/modules/adex/balances',
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

  async adexHistory(): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/blockchains/ETH/modules/adex/history',
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

  private async internalKrakenStaking<T>(
    pagination: KrakenStakingPagination,
    asyncQuery: boolean = false
  ): Promise<T> {
    const response = await this.axios.post<ActionResult<T>>(
      '/staking/kraken',
      axiosSnakeCaseTransformer({
        asyncQuery,
        ...pagination,
        orderByAttributes:
          pagination.orderByAttributes?.map(item =>
            getUpdatedKey(item, false)
          ) ?? []
      }),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  }

  async refreshKrakenStaking(): Promise<PendingTask> {
    return await this.internalKrakenStaking(emptyPagination(), true);
  }

  async fetchKrakenStakingEvents(
    pagination: KrakenStakingPagination
  ): Promise<KrakenStakingEvents> {
    const data = await this.internalKrakenStaking({
      ...pagination,
      onlyCache: true
    });
    return KrakenStakingEvents.parse(data);
  }

  async importFile(data: FormData): Promise<PendingTask> {
    const response = await this.axios.post<ActionResult<PendingTask>>(
      '/import',
      data,
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return handleResponse(response);
  }

  async queryBinanceMarkets(location: string): Promise<string[]> {
    const response = await this.axios.get<ActionResult<string[]>>(
      '/exchanges/binance/pairs',
      {
        params: axiosSnakeCaseTransformer({
          location: location
        })
      }
    );

    return handleResponse(response);
  }

  async queryBinanceUserMarkets(
    name: string,
    location: string
  ): Promise<string[]> {
    const response = await this.axios.get<ActionResult<string[]>>(
      `/exchanges/binance/pairs/${name}`,
      {
        params: axiosSnakeCaseTransformer({
          location: location
        })
      }
    );

    return handleResponse(response);
  }

  async downloadCSV(): Promise<ActionStatus> {
    try {
      const response = await this.axios.get('/history/download/', {
        responseType: 'blob',
        validateStatus: validTaskStatus
      });

      if (response.status === 200) {
        const url = window.URL.createObjectURL(response.data);
        downloadFileByUrl(url, 'reports.zip');
        return { success: true };
      }

      const body = await (response.data as Blob).text();
      const result: ActionResult<null> = JSON.parse(body);

      return { success: false, message: result.message };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  }

  async airdrops(): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/blockchains/ETH/airdrops',
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

  async ignoreActions(
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoredActions> {
    const response = await this.axios.put<ActionResult<IgnoredActions>>(
      '/actions/ignored',
      axiosSnakeCaseTransformer({
        actionIds,
        actionType
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return IgnoredActions.parse(handleResponse(response));
  }

  async unignoreActions(
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoredActions> {
    const response = await this.axios.delete<ActionResult<IgnoredActions>>(
      '/actions/ignored',
      {
        data: axiosSnakeCaseTransformer({
          actionIds,
          actionType
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return IgnoredActions.parse(handleResponse(response));
  }

  async erc20details(address: string): Promise<PendingTask> {
    const response = await this.axios.get<ActionResult<PendingTask>>(
      '/blockchains/ETH/erc20details/',
      {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          address
        }),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async fetchNfts(ignoreCache: boolean): Promise<PendingTask> {
    const params = Object.assign(
      {
        asyncQuery: true
      },
      ignoreCache ? { ignoreCache } : {}
    );
    const response = await this.axios.get<ActionResult<PendingTask>>('/nfts', {
      params: axiosSnakeCaseTransformer(params),
      validateStatus: validWithoutSessionStatus,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  }

  async getSnapshotData(timestamp: number): Promise<Snapshot> {
    const response = await this.axios.get<ActionResult<Snapshot>>(
      `/snapshots/${timestamp}`,
      {
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return Snapshot.parse(handleResponse(response));
  }

  async updateSnapshotData(
    timestamp: number,
    payload: SnapshotPayload
  ): Promise<boolean> {
    const response = await this.axios.patch<ActionResult<boolean>>(
      `/snapshots/${timestamp}`,
      axiosSnakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async exportSnapshotCSV({
    path,
    timestamp
  }: {
    path: string;
    timestamp: number;
  }): Promise<boolean> {
    const response = await this.axios.get<ActionResult<boolean>>(
      `/snapshots/${timestamp}`,
      {
        params: axiosSnakeCaseTransformer({
          path,
          action: 'export'
        }),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async downloadSnapshot(timestamp: number): Promise<any> {
    return this.axios.get<any>(`/snapshots/${timestamp}`, {
      params: axiosSnakeCaseTransformer({ action: 'download' }),
      validateStatus: validWithoutSessionStatus,
      responseType: 'arraybuffer'
    });
  }

  async deleteSnapshot(payload: { timestamp: number }): Promise<boolean> {
    const response = await this.axios.delete<ActionResult<boolean>>(
      '/snapshots',
      {
        data: axiosSnakeCaseTransformer(payload),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async fetchEthereumNodes(): Promise<EthereumRpcNodeList> {
    const response = await this.axios.get<ActionResult<EthereumRpcNodeList>>(
      '/blockchains/ETH/nodes'
    );
    return EthereumRpcNodeList.parse(handleResponse(response));
  }

  async addEthereumNode(
    node: Omit<EthereumRpcNode, 'identifier'>
  ): Promise<boolean> {
    const response = await this.axios.put<ActionResult<boolean>>(
      '/blockchains/ETH/nodes',
      axiosSnakeCaseTransformer(node),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  }

  async editEthereumNode(node: EthereumRpcNode): Promise<boolean> {
    const response = await this.axios.post<ActionResult<boolean>>(
      '/blockchains/ETH/nodes',
      axiosSnakeCaseTransformer(node),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  }

  async deleteEthereumNode(identifier: number): Promise<boolean> {
    const response = await this.axios.delete<ActionResult<boolean>>(
      '/blockchains/ETH/nodes',
      {
        data: axiosSnakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  }

  async backendSettings(): Promise<BackendConfiguration> {
    const response = await this.axios.get<ActionResult<BackendConfiguration>>(
      '/settings/configuration',
      {
        transformResponse: basicAxiosTransformer
      }
    );
    return BackendConfiguration.parse(handleResponse(response));
  }
}

export const api = new RotkehlchenApi();
