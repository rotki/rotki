<template>
  <progress-screen v-if="loading">
    <template #message>{{ tc('borrowing.loading') }}</template>
  </progress-screen>
  <div v-else>
    <v-row class="mt-8">
      <v-col>
        <refresh-header
          :title="tc('borrowing.header')"
          :loading="refreshing"
          @refresh="refresh()"
        >
          <template #actions>
            <active-modules :modules="modules" />
          </template>
        </refresh-header>
      </v-col>
    </v-row>
    <v-row no-gutters class="mt-6">
      <v-col cols="12">
        <stat-card-wide :cols="2">
          <template #first-col>
            <stat-card-column>
              <template #title>
                {{ tc('borrowing.total_collateral_locked') }}
              </template>
              <amount-display
                :value="summary.totalCollateralUsd"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </stat-card-column>
          </template>
          <template #second-col>
            <stat-card-column>
              <template #title>
                {{ tc('borrowing.total_outstanding_debt') }}
              </template>
              <amount-display
                :value="summary.totalDebt"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </stat-card-column>
          </template>
        </stat-card-wide>
      </v-col>
    </v-row>
    <v-row no-gutters class="mt-8">
      <v-col cols="12" md="6" class="pe-md-4">
        <v-card>
          <div class="mx-4 pt-4">
            <v-autocomplete
              v-model="selection"
              class="borrowing__vault-selection"
              :label="tc('borrowing.select_loan')"
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
                <defi-selector-item :item="item" />
              </template>
              <template #item="{ item }">
                <defi-selector-item :item="item" />
              </template>
            </v-autocomplete>
          </div>
          <v-card-text>{{ tc('borrowing.select_loan_hint') }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
        <defi-protocol-selector v-model="protocol" liabilities />
      </v-col>
    </v-row>
    <loan-info v-if="loan" :loan="loan" />
    <full-size-content v-else>
      <v-row align="center" justify="center">
        <v-col class="text-h6">{{ tc('liabilities.no_selection') }}</v-col>
      </v-row>
    </full-size-content>
  </div>
</template>

<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import DefiSelectorItem from '@/components/defi/DefiSelectorItem.vue';
import LoanInfo from '@/components/defi/loan/LoanInfo.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCardColumn from '@/components/display/StatCardColumn.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import DefiProtocolSelector from '@/components/helper/DefiProtocolSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { useSectionLoading } from '@/composables/common';
import { useDefiSupportedProtocolsStore } from '@/store/defi/protocols';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

defineProps({
  modules: { required: true, type: Array as PropType<Module[]> }
});

const selection = ref<string>();
const protocol = ref<DefiProtocol | null>(null);
const store = useDefiSupportedProtocolsStore();
const route = useRoute();
const { tc } = useI18n();

const { shouldShowLoadingScreen, isSectionRefreshing } = useSectionLoading();

const loading = shouldShowLoadingScreen(Section.DEFI_BORROWING);

const selectedProtocols = computed(() => {
  const selected = get(protocol);
  return selected ? [selected] : [];
});

const loan = computed(() => get(store.loan(get(selection))));

const loans = computed(() => {
  const protocols = get(selectedProtocols);
  return get(store.loans(protocols));
});

const summary = computed(() => {
  const protocols = get(selectedProtocols);
  return get(store.loanSummary(protocols));
});

const refreshing = computed(() => {
  return (
    get(isSectionRefreshing(Section.DEFI_BORROWING)) ||
    get(isSectionRefreshing(Section.DEFI_BORROWING_HISTORY))
  );
});

const refresh = async () => {
  await store.fetchBorrowing(true);
};

onMounted(async () => {
  const currentRoute = get(route);
  const queryElement = currentRoute.query['protocol'];
  const protocols = Object.values(DefiProtocol);
  const protocolIndex = protocols.findIndex(
    protocol => protocol === queryElement
  );
  if (protocolIndex >= 0) {
    set(protocol, protocols[protocolIndex]);
  }
  await store.fetchBorrowing(false);
});
</script>
