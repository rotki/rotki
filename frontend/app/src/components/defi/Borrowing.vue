<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type Module } from '@/types/modules';
import { Section } from '@/types/status';

defineProps<{
  modules: Module[];
}>();

const selection = ref<string>();
const protocol = ref<DefiProtocol | null>(null);
const defiLending = useDefiLending();
const route = useRoute();
const { t } = useI18n();

const { shouldShowLoadingScreen, isLoading } = useStatusStore();

const loading = shouldShowLoadingScreen(Section.DEFI_BORROWING);

const selectedProtocols = computed(() => {
  const selected = get(protocol);
  return selected ? [selected] : [];
});

const loan = computed(() => get(defiLending.loan(get(selection))));

const loans = computed(() => {
  const protocols = get(selectedProtocols);
  return get(defiLending.loans(protocols));
});

const summary = computed(() => {
  const protocols = get(selectedProtocols);
  return get(defiLending.loanSummary(protocols));
});

const refreshing = logicOr(
  isLoading(Section.DEFI_BORROWING),
  isLoading(Section.DEFI_BORROWING_HISTORY)
);

const refresh = async () => {
  await defiLending.fetchBorrowing(true);
};

onMounted(async () => {
  const currentRoute = get(route);
  const queryElement = currentRoute.query['protocol'];
  const protocols = Object.values(DefiProtocol);
  const protocolIndex = protocols.indexOf(queryElement as DefiProtocol);
  if (protocolIndex >= 0) {
    set(protocol, protocols[protocolIndex]);
  }
  await defiLending.fetchBorrowing(false);
});

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('borrowing.header').toLocaleLowerCase()
  })
);
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.defi'), t('borrowing.header')]">
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
      <template #message>{{ t('borrowing.loading') }}</template>
    </ProgressScreen>

    <div v-else class="flex flex-col gap-4">
      <StatCardWide :cols="2">
        <template #first-col>
          <StatCardColumn>
            <template #title>
              {{ t('borrowing.total_collateral_locked') }}
            </template>
            <AmountDisplay
              :value="summary.totalCollateralUsd"
              show-currency="symbol"
              fiat-currency="USD"
            />
          </StatCardColumn>
        </template>
        <template #second-col>
          <StatCardColumn>
            <template #title>
              {{ t('borrowing.total_outstanding_debt') }}
            </template>
            <AmountDisplay
              :value="summary.totalDebt"
              show-currency="symbol"
              fiat-currency="USD"
            />
          </StatCardColumn>
        </template>
      </StatCardWide>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <RuiCard>
          <VAutocomplete
            v-model="selection"
            class="borrowing__vault-selection"
            :label="t('borrowing.select_loan')"
            chips
            dense
            outlined
            item-key="identifier"
            :items="loans"
            item-text="identifier"
            hide-details
            clearable
            :open-on-clear="false"
          >
            <template #selection="{ item }">
              <DefiSelectorItem :item="item" />
            </template>
            <template #item="{ item }">
              <DefiSelectorItem :item="item" />
            </template>
          </VAutocomplete>
          <div class="p-2 text-body-2 text-rui-text-secondary">
            {{ t('borrowing.select_loan_hint') }}
          </div>
        </RuiCard>
        <DefiProtocolSelector v-model="protocol" liabilities />
      </div>

      <LoanInfo v-if="loan" :loan="loan" />

      <FullSizeContent v-else>
        <div class="flex h-full text-h6 items-center justify-center">
          {{ t('liabilities.no_selection') }}
        </div>
      </FullSizeContent>
    </div>
  </TablePageLayout>
</template>
