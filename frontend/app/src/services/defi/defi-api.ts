import { AxiosInstance, AxiosResponseTransformer } from 'axios';
import { setupTransformer } from '@/services/axios-tranformers';
import { ProtocolVersion } from '@/services/defi/consts';
import { ApiImplementation, PendingTask } from '@/services/types-api';
import { fetchExternalAsync } from '@/services/utils';

export class DefiApi {
  private readonly axios: AxiosInstance;
  private readonly baseTransformer: AxiosResponseTransformer[];

  private get api(): ApiImplementation {
    return {
      axios: this.axios,
      baseTransformer: this.baseTransformer
    };
  }

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.baseTransformer = setupTransformer();
  }

  async dsrBalance(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/makerdao/dsrbalance';
    return fetchExternalAsync(this.api, url);
  }

  async dsrHistory(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/makerdao/dsrhistory';
    return fetchExternalAsync(this.api, url);
  }

  async makerDAOVaults(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/makerdao/vaults';
    return fetchExternalAsync(this.api, url);
  }

  async makerDAOVaultDetails(): Promise<PendingTask> {
    const url = '/blockchains/ETH/modules/makerdao/vaultdetails';
    return fetchExternalAsync(this.api, url);
  }

  async fetchAaveBalances(): Promise<PendingTask> {
    const url = '/blockchains/ETH/modules/aave/balances';
    return fetchExternalAsync(this.api, url);
  }

  async fetchAaveHistory(reset?: boolean): Promise<PendingTask> {
    const url = '/blockchains/ETH/modules/aave/history';
    const params = reset ? { resetDbData: true } : undefined;
    return fetchExternalAsync(this.api, url, params);
  }

  async fetchAllDefi(): Promise<PendingTask> {
    return fetchExternalAsync(this.api, '/blockchains/ETH/defi');
  }

  async fetchCompoundBalances(): Promise<PendingTask> {
    const url = '/blockchains/ETH/modules/compound/balances';
    return fetchExternalAsync(this.api, url);
  }

  async fetchCompoundHistory(): Promise<PendingTask> {
    const url = '/blockchains/ETH/modules/compound/history';
    return fetchExternalAsync(this.api, url);
  }

  async fetchYearnVaultsHistory(
    protocolVersion: ProtocolVersion = ProtocolVersion.V1,
    reset?: boolean
  ): Promise<PendingTask> {
    const path = protocolVersion === ProtocolVersion.V1 ? 'vaults' : 'vaultsv2';
    const url = `/blockchains/ETH/modules/yearn/${path}/history`;
    const params = reset ? { resetDbData: true } : undefined;
    return fetchExternalAsync(this.api, url, params);
  }

  async fetchYearnVaultsBalances(
    protocolVersion: ProtocolVersion = ProtocolVersion.V1
  ): Promise<PendingTask> {
    const path = protocolVersion === ProtocolVersion.V1 ? 'vaults' : 'vaultsv2';
    const url = `/blockchains/ETH/modules/yearn/${path}/balances`;
    return fetchExternalAsync(this.api, url);
  }

  async fetchUniswapTrades(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/uniswap/history/trades';
    return fetchExternalAsync(this.api, url);
  }

  async fetchUniswapBalances(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/uniswap/balances';
    return fetchExternalAsync(this.api, url);
  }

  async fetchUniswapEvents(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/uniswap/history/events';
    return fetchExternalAsync(this.api, url);
  }

  async fetchBalancerBalances(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/balancer/balances';
    return fetchExternalAsync(this.api, url);
  }

  async fetchBalancerTrades(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/balancer/history/trades';
    return fetchExternalAsync(this.api, url);
  }

  async fetchBalancerEvents(): Promise<PendingTask> {
    const url = '/blockchains/ETH/modules/balancer/history/events';
    return fetchExternalAsync(this.api, url);
  }

  async fetchSushiswapBalances() {
    const url = 'blockchains/ETH/modules/sushiswap/balances';
    return fetchExternalAsync(this.api, url);
  }

  async fetchSushiswapTrades(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/sushiswap/history/trades';
    return fetchExternalAsync(this.api, url);
  }

  async fetchSushiswapEvents(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/sushiswap/history/events';
    return fetchExternalAsync(this.api, url);
  }

  async fetchLiquityBalances(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/liquity/balances';
    return fetchExternalAsync(this.api, url);
  }

  async fetchLiquityTroveEvents(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/liquity/events/trove';
    return fetchExternalAsync(this.api, url);
  }

  fetchLiquityStaking(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/liquity/staking';
    return fetchExternalAsync(this.api, url);
  }

  fetchLiquityStakingEvents(): Promise<PendingTask> {
    const url = 'blockchains/ETH/modules/liquity/events/staking';
    return fetchExternalAsync(this.api, url);
  }
}
