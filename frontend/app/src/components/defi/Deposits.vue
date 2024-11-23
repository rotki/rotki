<script setup lang="ts">
import { type BigNumber, Blockchain, HistoryEventEntryType } from '@rotki/common';
import { DefiProtocol, Module, isDefiProtocol } from '@/types/modules';
import { Section } from '@/types/status';
import { ProtocolVersion } from '@/types/defi';
import { AaveEarnedDetails, CompoundLendingDetails } from '@/premium/premium';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useDefiStore } from '@/store/defi';
import { useAaveStore } from '@/store/defi/aave';
import { useStatusStore } from '@/store/status';
import { usePremium } from '@/composables/premium';
import { useDefiLending } from '@/composables/defi/lending';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import YearnAssetsTable from '@/components/defi/yearn/YearnAssetsTable.vue';
import LendingAssetTable from '@/components/defi/display/LendingAssetTable.vue';
import StatCard from '@/components/display/StatCard.vue';
import DefiProtocolSelector from '@/components/defi/DefiProtocolSelector.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import DepositTotals from '@/components/defi/DepositTotals.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';

const section = Section.DEFI_LENDING;
const historySection = Section.DEFI_LENDING_HISTORY;

const modules: Module[] = [Module.AAVE, Module.COMPOUND, Module.YEARN, Module.YEARN_V2, Module.MAKERDAO_DSR];

const chains = [Blockchain.ETH];

const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
const protocol = ref<DefiProtocol>();
const premium = usePremium();
const route = useRoute();
const { isLoading, shouldShowLoadingScreen } = useStatusStore();

const defiStore = useDefiStore();
const defiLending = useDefiLending();
const aaveStore = useAaveStore();

const { t } = useI18n();

const selectedAddresses = useArrayMap(selectedAccounts, account => getAccountAddress(account));
const accountFilter = useArrayMap(selectedAccounts, account => ({
  address: getAccountAddress(account),
  chain: account.chain,
}));

const selectedProtocols = computed(() => {
  const selected = get(protocol);
  return selected ? [selected] : [];
});

const defiAddresses = computed(() => {
  const protocols = get(selectedProtocols);
  return get(defiStore.defiAccounts(protocols)).map(({ data: { address } }) => address);
});

const lendingBalances = computed(() => {
  const protocols = get(selectedProtocols);
  const addresses = get(selectedAddresses);
  return get(defiLending.aggregatedLendingBalances(protocols, addresses));
});

const totalEarnedInAave = computed(() => get(aaveStore.aaveTotalEarned(get(selectedAddresses))));

const effectiveInterestRate = computed<BigNumber>(() => {
  const protocols = get(selectedProtocols);
  const addresses = get(selectedAddresses);
  return bigNumberify(get(defiLending.effectiveInterestRate(protocols, addresses)));
});

const totalLendingDeposit = computed<BigNumber>(() => {
  const protocols = get(selectedProtocols);
  const addresses = get(selectedAddresses);
  return get(defiLending.totalLendingDeposit(protocols, addresses));
});

const totalUsdEarned = computed<BigNumber>(() => {
  const protocols = get(selectedProtocols);
  const addresses = get(selectedAddresses);
  return get(defiLending.totalUsdEarned(protocols, addresses));
});

function isProtocol(protocol: DefiProtocol) {
  return computed(() => {
    const protocols = get(selectedProtocols);
    return protocols.length > 0 && protocols.includes(protocol);
  });
}

const isCompound = isProtocol(DefiProtocol.COMPOUND);
const isAave = isProtocol(DefiProtocol.AAVE);
const isYearnVaults = isProtocol(DefiProtocol.YEARN_VAULTS);
const isYearnVaultsV2 = isProtocol(DefiProtocol.YEARN_VAULTS_V2);
const isYearn = logicOr(isYearnVaults, isYearnVaultsV2);
const noProtocolSelection = computed(() => get(selectedProtocols).length === 0);

const yearnVersion = computed(() => {
  if (get(isYearnVaults))
    return ProtocolVersion.V1;
  else if (get(isYearnVaultsV2))
    return ProtocolVersion.V2;

  return null;
});

const loading = shouldShowLoadingScreen(section);
const historyLoading = shouldShowLoadingScreen(historySection);
const historyRefreshing = isLoading(historySection);

const refreshing = logicOr(isLoading(section), historyRefreshing);

async function refresh() {
  await defiLending.fetchLending(true);
}

onMounted(async () => {
  const currentRoute = get(route);
  const queryElement = currentRoute.query.protocol;
  if (isDefiProtocol(queryElement))
    set(protocol, queryElement);

  await defiLending.fetchLending();
});

const transactionEventProtocols = computed<string[]>(() => {
  const selectedProtocol = get(protocol);

  const mapping: { [key in DefiProtocol]?: string[] } = {
    [DefiProtocol.AAVE]: ['aave-v1', 'aave-v2', 'aave-v3'],
    [DefiProtocol.COMPOUND]: ['compound', 'compound-v3'],
    [DefiProtocol.MAKERDAO_DSR]: ['makerdao dsr'],
    [DefiProtocol.YEARN_VAULTS]: ['yearn-v1'],
    [DefiProtocol.YEARN_VAULTS_V2]: ['yearn-v2'],
  };

  if (!selectedProtocol)
    return Object.values(mapping).flat();

  const mappedProtocol = mapping[selectedProtocol];
  assert(mappedProtocol);

  return mappedProtocol;
});

const refreshTooltip = computed<string>(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('common.deposits').toLocaleLowerCase(),
  }),
);
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.defi'), t('common.deposits'), t('navigation_menu.defi_sub.deposits_sub.protocols')]"
  >
    <template #buttons>
      <div class="flex items-center gap-4">
        <ActiveModules :modules="modules" />

        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="loading || refreshing"
              @click="refresh()"
            >
              <template #prepend>
                <RuiIcon name="lu-refresh-ccw" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ refreshTooltip }}
        </RuiTooltip>
      </div>
    </template>

    <ProgressScreen v-if="loading">
      <template #message>
        {{ t('lending.loading') }}
      </template>
    </ProgressScreen>

    <div
      v-else
      class="flex flex-col gap-4"
    >
      <RuiAlert
        type="warning"
        :title="t('common.important_notice')"
        class="mb-2"
      >
        {{ t('decentralized_overview.deprecated_warning') }}
      </RuiAlert>
      <DepositTotals
        :loading="historyLoading"
        :effective-interest-rate="effectiveInterestRate"
        :total-lending-deposit="totalLendingDeposit"
        :total-usd-earned="totalUsdEarned"
      />

      <div class="grid md:grid-cols-2 gap-4">
        <BlockchainAccountSelector
          v-model="selectedAccounts"
          hint
          outlined
          dense
          :chains="chains"
          :usable-addresses="defiAddresses"
        />
        <DefiProtocolSelector v-model="protocol" />
      </div>

      <StatCard
        v-if="!isYearn"
        :title="t('common.assets')"
      >
        <LendingAssetTable
          :loading="refreshing"
          :assets="lendingBalances"
        />
      </StatCard>

      <YearnAssetsTable
        v-if="isYearn || noProtocolSelection"
        :version="yearnVersion"
        :loading="refreshing"
        :selected-addresses="selectedAddresses"
      />

      <template v-if="premium">
        <CompoundLendingDetails
          v-if="isCompound"
          :addresses="selectedAddresses"
        />

        <AaveEarnedDetails
          v-if="(isAave || noProtocolSelection) && totalEarnedInAave.length > 0"
          :profit="totalEarnedInAave"
        />
      </template>

      <PremiumCard
        v-if="!premium"
        :title="t('lending.history')"
      />

      <HistoryEventsView
        v-else
        use-external-account-filter
        :section-title="t('common.events')"
        :protocols="transactionEventProtocols"
        :external-account-filter="accountFilter"
        :only-chains="chains"
        :entry-types="[HistoryEventEntryType.EVM_EVENT]"
      />
    </div>
  </TablePageLayout>
</template>
