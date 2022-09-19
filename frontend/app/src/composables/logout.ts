import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useNonFungibleBalancesStore } from '@/store/balances/non-funginble';
import { useBtcAccountsStore } from '@/store/blockchain/accounts/btc';
import { useChainsAccountsStore } from '@/store/blockchain/accounts/chains';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useBtcBalancesStore } from '@/store/blockchain/balances/btc';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useDefiStore } from '@/store/defi';
import { useHistory } from '@/store/history';
import { useTxQueryStatus } from '@/store/history/query-status';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useReports } from '@/store/reports';
import { useSessionStore } from '@/store/session';
import { usePeriodicStore } from '@/store/session/periodic';
import { usePremiumStore } from '@/store/session/premium';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useTagStore } from '@/store/session/tags';
import { useWatchersStore } from '@/store/session/watchers';
import { useSettingsStore } from '@/store/settings';
import { useStakingStore } from '@/store/staking';
import { useStatisticsStore } from '@/store/statistics';
import { useStatusStore } from '@/store/status';
import { useTasks } from '@/store/tasks';

//TODO: find a better way to reset all stores
export const useSessionStateCleaner = () => {
  const { logged } = storeToRefs(useSessionStore());

  watch(logged, logged => {
    if (logged) {
      return;
    }
    usePremiumStore().reset();
    useQueriedAddressesStore().reset();
    useTagStore().reset();
    useWatchersStore().reset();
    useEthNamesStore().reset();
    useStatusStore().reset();
    usePeriodicStore().reset();
    useMainStore().reset();
    useSettingsStore().reset();
    useDefiStore().reset();
    useStakingStore().reset();
    useStatisticsStore().reset();
    useHistory().reset();
    useTxQueryStatus().reset();
    useNotifications().reset();
    useReports().reset();
    useTasks().reset();
    useNonFungibleBalancesStore().reset();
    useBtcAccountsStore().reset();
    useEthAccountsStore().reset();
    useChainsAccountsStore().reset();
    useBtcBalancesStore().reset();
    useEthBalancesStore().reset();
    useChainsAccountsStore().reset();
    useBlockchainTokensStore().reset();
  });
};
