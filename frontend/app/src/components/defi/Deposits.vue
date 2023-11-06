<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain, DefiProtocol } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type YearnVaultProfitLoss } from '@/types/defi/yearn';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { ProtocolVersion } from '@/types/defi';
import {
  AaveEarnedDetails,
  CompoundLendingDetails,
  YearnVaultsProfitDetails
} from '@/premium/premium';

const section = Section.DEFI_LENDING;
const historySection = Section.DEFI_LENDING_HISTORY;

const modules: Module[] = [
  Module.AAVE,
  Module.COMPOUND,
  Module.YEARN,
  Module.YEARN_V2,
  Module.MAKERDAO_DSR
];

const chains = [Blockchain.ETH];

const selectedAccounts = ref<GeneralAccount[]>([]);
const protocol = ref<DefiProtocol | null>(null);
const premium = usePremium();
const route = useRoute();
const { shouldShowLoadingScreen, isLoading } = useStatusStore();

const defiStore = useDefiStore();
const defiLending = useDefiLending();
const yearnStore = useYearnStore();
const aaveStore = useAaveStore();

const { t } = useI18n();

const isProtocol = (protocol: DefiProtocol) =>
  computed(() => {
    const protocols = get(selectedProtocols);
    return protocols.length > 0 && protocols.includes(protocol);
  });

const selectedAddresses = useArrayMap(selectedAccounts, a => a.address);

const selectedProtocols = computed(() => {
  const selected = get(protocol);
  return selected ? [selected] : [];
});

const defiAddresses = computed(() => {
  const protocols = get(selectedProtocols);
  return get(defiStore.defiAccounts(protocols)).map(({ address }) => address);
});

const lendingBalances = computed(() => {
  const protocols = get(selectedProtocols);
  const addresses = get(selectedAddresses);
  return get(defiLending.aggregatedLendingBalances(protocols, addresses));
});

const totalEarnedInAave = computed(() =>
  get(aaveStore.aaveTotalEarned(get(selectedAddresses)))
);

const effectiveInterestRate = computed<string>(() => {
  const protocols = get(selectedProtocols);
  const addresses = get(selectedAddresses);
  return get(defiLending.effectiveInterestRate(protocols, addresses));
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

const isCompound = isProtocol(DefiProtocol.COMPOUND);
const isAave = isProtocol(DefiProtocol.AAVE);
const isYearnVaults = isProtocol(DefiProtocol.YEARN_VAULTS);
const isYearnVaultsV2 = isProtocol(DefiProtocol.YEARN_VAULTS_V2);
const isYearn = logicAnd(isYearnVaults, isYearnVaultsV2);
const noProtocolSelection = computed(() => get(selectedProtocols).length === 0);

const yearnVersion = computed(() => {
  if (get(isYearnVaults)) {
    return ProtocolVersion.V1;
  } else if (get(isYearnVaultsV2)) {
    return ProtocolVersion.V2;
  }
  return null;
});

const yearnProfit = computed(() => {
  const protocols = get(selectedProtocols);
  const allSelected = protocols.length === 0;
  const addresses = get(selectedAddresses);
  let v1Profit: YearnVaultProfitLoss[] = [];
  if (get(isYearnVaults) || allSelected) {
    v1Profit = get(yearnStore.yearnVaultsProfit(addresses, ProtocolVersion.V1));
  }

  let v2Profit: YearnVaultProfitLoss[] = [];
  if (get(isYearnVaultsV2) || allSelected) {
    v2Profit = get(yearnStore.yearnVaultsProfit(addresses, ProtocolVersion.V2));
  }
  return [...v1Profit, ...v2Profit];
});

const loading = shouldShowLoadingScreen(section);
const historyLoading = shouldShowLoadingScreen(historySection);
const historyRefreshing = isLoading(historySection);

const refreshing = logicOr(isLoading(section), historyRefreshing);

const refresh = async () => {
  await defiLending.fetchLending(true);
};

onMounted(async () => {
  const currentRoute = get(route);
  const queryElement = currentRoute.query['protocol'];
  const protocols = Object.values(DefiProtocol);
  const protocolIndex = protocols.indexOf(queryElement as DefiProtocol);
  if (protocolIndex >= 0) {
    set(protocol, protocols[protocolIndex]);
  }
  await defiLending.fetchLending();
});

const transactionEventProtocols: ComputedRef<string[]> = computed(() => {
  const selectedProtocol = get(protocol);

  const mapping: { [key in DefiProtocol]?: string[] } = {
    [DefiProtocol.AAVE]: ['aave-v1', 'aave-v2'],
    [DefiProtocol.COMPOUND]: ['compound'],
    [DefiProtocol.MAKERDAO_DSR]: ['makerdao dsr'],
    [DefiProtocol.YEARN_VAULTS]: ['yearn-v1'],
    [DefiProtocol.YEARN_VAULTS_V2]: ['yearn-v2']
  };

  if (selectedProtocol === null) {
    return Object.values(mapping).flat();
  }

  const mappedProtocol = mapping[selectedProtocol];
  assert(mappedProtocol);

  return mappedProtocol;
});

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('common.deposits').toLocaleLowerCase()
  })
);
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.defi'),
      t('common.deposits'),
      t('navigation_menu.defi_sub.deposits_sub.protocols')
    ]"
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
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ refreshTooltip }}
        </RuiTooltip>
      </div>
    </template>

    <ProgressScreen v-if="loading">
      <template #message>{{ t('lending.loading') }}</template>
    </ProgressScreen>

    <div v-else class="flex flex-col gap-4">
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

      <StatCard v-if="!isYearn" :title="t('common.assets')">
        <LendingAssetTable :loading="refreshing" :assets="lendingBalances" />
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

        <YearnVaultsProfitDetails
          v-if="(isYearn || noProtocolSelection) && yearnProfit.length > 0"
          :profit="yearnProfit"
        />

        <AaveEarnedDetails
          v-if="(isAave || noProtocolSelection) && totalEarnedInAave.length > 0"
          :profit="totalEarnedInAave"
        />
      </template>

      <PremiumCard v-if="!premium" :title="t('lending.history')" />

      <HistoryEventsView
        v-else
        use-external-account-filter
        :section-title="t('common.events')"
        :protocols="transactionEventProtocols"
        :external-account-filter="selectedAccounts"
        :only-chains="chains"
        :entry-types="[HistoryEventEntryType.EVM_EVENT]"
      />
    </div>
  </TablePageLayout>
</template>
