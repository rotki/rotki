<script setup lang="ts">
import { type DefiProtocol, type Module, isDefiProtocol } from '@/types/modules';
import { Section } from '@/types/status';

defineProps<{
  modules: Module[];
}>();

const selection = ref<string>();
const protocol = ref<DefiProtocol>();
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

const refreshing = logicOr(isLoading(Section.DEFI_BORROWING), isLoading(Section.DEFI_BORROWING_HISTORY));

async function refresh() {
  await defiLending.fetchBorrowing(true);
}

onMounted(async () => {
  const currentRoute = get(route);
  const queryElement = currentRoute.query.protocol;
  if (isDefiProtocol(queryElement))
    set(protocol, queryElement);

  await defiLending.fetchBorrowing(false);
});

const refreshTooltip = computed<string>(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('borrowing.header').toLocaleLowerCase(),
  }),
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
      <template #message>
        {{ t('borrowing.loading') }}
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
      <StatCardWide>
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
      </StatCardWide>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <RuiCard>
          <RuiAutoComplete
            v-model="selection"
            class="borrowing__vault-selection"
            :label="t('borrowing.select_loan')"
            dense
            variant="outlined"
            key-attr="identifier"
            text-attr="identifier"
            :options="loans"
            hide-details
            clearable
            auto-select-first
            :item-height="40"
          >
            <template #selection="{ item }">
              <DefiSelectorItem :item="item" />
            </template>
            <template #item="{ item }">
              <DefiSelectorItem
                class="py-1"
                :item="item"
              />
            </template>
          </RuiAutoComplete>
          <div class="p-2 text-body-2 text-rui-text-secondary">
            {{ t('borrowing.select_loan_hint') }}
          </div>
        </RuiCard>
        <DefiProtocolSelector
          v-model="protocol"
          liabilities
        />
      </div>

      <LoanInfo
        v-if="loan"
        :loan="loan"
      />

      <FullSizeContent v-else>
        <div class="flex h-full text-h6 items-center justify-center">
          {{ t('liabilities.no_selection') }}
        </div>
      </FullSizeContent>
    </div>
  </TablePageLayout>
</template>
