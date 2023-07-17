<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type PropType } from 'vue';
import { type Module } from '@/types/modules';
import { Section } from '@/types/status';

defineProps({
  modules: { required: true, type: Array as PropType<Module[]> }
});

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
</script>

<template>
  <ProgressScreen v-if="loading">
    <template #message>{{ t('borrowing.loading') }}</template>
  </ProgressScreen>
  <div v-else>
    <VRow class="mt-8">
      <VCol>
        <RefreshHeader
          :title="t('borrowing.header')"
          :loading="refreshing"
          @refresh="refresh()"
        >
          <template #actions>
            <ActiveModules :modules="modules" />
          </template>
        </RefreshHeader>
      </VCol>
    </VRow>
    <VRow no-gutters class="mt-6">
      <VCol cols="12">
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
      </VCol>
    </VRow>
    <VRow no-gutters class="mt-8">
      <VCol cols="12" md="6" class="pe-md-4">
        <VCard>
          <div class="mx-4 pt-4">
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
          </div>
          <VCardText>{{ t('borrowing.select_loan_hint') }}</VCardText>
        </VCard>
      </VCol>
      <VCol cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
        <DefiProtocolSelector v-model="protocol" liabilities />
      </VCol>
    </VRow>
    <LoanInfo v-if="loan" :loan="loan" />
    <FullSizeContent v-else>
      <VRow align="center" justify="center">
        <VCol class="text-h6">{{ t('liabilities.no_selection') }}</VCol>
      </VRow>
    </FullSizeContent>
  </div>
</template>
