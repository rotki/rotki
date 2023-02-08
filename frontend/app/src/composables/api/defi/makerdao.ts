import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useMakerDaoApi = () => {
  const fetchDsrBalances = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/makerdao/dsrbalance';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchDsrHistories = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/makerdao/dsrhistory';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchMakerDAOVaults = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/makerdao/vaults';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchMakerDAOVaultDetails = async (): Promise<PendingTask> => {
    const url = '/blockchains/ETH/modules/makerdao/vaultdetails';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchDsrBalances,
    fetchDsrHistories,
    fetchMakerDAOVaults,
    fetchMakerDAOVaultDetails
  };
};
