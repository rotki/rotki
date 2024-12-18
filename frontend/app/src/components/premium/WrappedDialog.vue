<script setup lang="ts">
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import HashLink from '@/components/helper/HashLink.vue';
import AppImage from '@/components/common/AppImage.vue';
import { usePremium } from '@/composables/premium';
import { type WrapStatisticsResult, useWrapStatisticsApi } from '@/composables/api/statistics/wrap';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { useStatusStore } from '@/store/status';
import { useCurrencies } from '@/types/currencies';
import { useSupportedChains } from '@/composables/info/chains';
import CounterpartyDisplay from '../history/CounterpartyDisplay.vue';

const props = defineProps<{
  display: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:display', value: boolean): void;
  (e: 'close'): void;
}>();

const { t } = useI18n();
const premium = usePremium();
const { apiKey } = useExternalApiKeys(t);
const { isTaskRunning } = useTaskStore();
const { isLoading: isSectionLoading } = useStatusStore();
const { findCurrency } = useCurrencies();
const { fetchWrapStatistics } = useWrapStatisticsApi();
const { getChainName } = useSupportedChains();

const gnosisPayKey = computed(() => apiKey('gnosis_pay'));
const showGnosisData = computed(() => get(premium) && gnosisPayKey.value);

const loading = ref(false);
const summary = ref<WrapStatisticsResult | null>(null);
const loadingProgress = ref('0');

const isDecoding = computed(() => get(isTaskRunning(TaskType.TRANSACTIONS_DECODING)));
const sectionLoading = computed(() => isSectionLoading(Section.HISTORY_EVENT));
const refreshing = computed(() => get(sectionLoading) || get(isDecoding));

const currencyDisplayInfo = computed(() => {
  if (!summary.value?.gnosisMaxPaymentsByCurrency) {
    return [];
  }

  const result: Array<{
    amount: number;
    code: string;
    name: string;
    symbol: string;
  }> = [];

  for (const [code, amount] of Object.entries(summary.value.gnosisMaxPaymentsByCurrency)) {
    try {
      const currency = findCurrency(code);
      result.push({
        amount: parseFloat(amount),
        code,
        name: currency.name,
        symbol: currency.unicodeSymbol,
      });
    }
    catch {
      continue;
    }
  }

  return result;
});

async function fetchData() {
  if (!get(premium) || loading.value)
    return;

  try {
    loading.value = true;
    const response = await fetchWrapStatistics();
    summary.value = response;
  }
  catch {
    summary.value = null;
  }
  finally {
    loading.value = false;
  }
}

function hasSectionData(data: Record<string, any> | Array<any> | undefined): boolean {
  if (!data)
    return false;
  if (Array.isArray(data))
    return data.length > 0;
  return Object.keys(data).length > 0;
}

function closeDialog() {
  emit('update:display', false);
  emit('close');
}

function formatDate(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

watch(() => props.display, async (newVal) => {
  if (newVal) {
    await fetchData();
  }
});

onMounted(async () => {
  if (props.display && !summary.value) {
    await fetchData();
  }
});
</script>

<template>
  <BigDialog
    :display="display"
    :title="t('wrapped.title')"
    :subtitle="t('wrapped.subtitle')"
    :loading="loading"
    :action-hidden="true"
    :secondary-action="t('common.actions.close')"
    max-width="1000px"
    @cancel="closeDialog()"
    @close="closeDialog()"
  >
    <template v-if="premium">
      <div v-if="loading">
        <ProgressScreen :progress="loadingProgress">
          <template #message>
            {{ t('common.loading') }}
          </template>
        </ProgressScreen>
      </div>
      <div v-else-if="!summary">
        <div class="p-4 text-center">
          <p>{{ t('common.no_data') }}</p>
          <p class="mt-4 text-xs">
            {{ t('common.status') }}: {{ JSON.stringify({
              loading,
              premium: get(premium),
              summaryExists: !!summary,
            }, null, 2) }}
          </p>
        </div>
      </div>
      <div
        v-else
        class="flex flex-col gap-8 py-4 px-2"
      >
        <div class="py-8 w-full rounded-lg flex flex-col items-center bg-gradient-to-br from-rui-primary/5 to-rui-primary/10 dark:from-rui-primary-darker/5 dark:to-rui-primary-darker/10">
          <div class="absolute top-4 right-4">
            <RuiButton
              variant="text"
              color="primary"
              :loading="get(refreshing)"
              :disabled="get(refreshing)"
              @click="fetchData()"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </div>
          <RotkiLogo
            :size="3"
            class="mb-6"
          />
          <h2 class="text-4xl font-bold mb-2">
            {{ t('wrapped.title') }}
          </h2>
          <p class="text-xl text-rui-text-secondary">
            {{ t('wrapped.year_subtitle') }}
          </p>
        </div>

        <div
          v-if="summary.ethOnGas"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <RuiIcon
              name="gas-station-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium ">
              {{ t('wrapped.gas_spent_total') }}
            </h3>
          </div>
          <div class="text-xl font-bold mb-4 ">
            {{ summary.ethOnGas }}{{ t('staking.eth2') }}
          </div>
        </div>

        <div
          v-if="hasSectionData(summary.ethOnGasPerAddress)"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <RuiIcon
              name="wallet-3-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.gas_spent') }}
            </h3>
          </div>
          <div class="grid gap-2">
            <div
              v-for="[address, gas] in Object.entries(summary.ethOnGasPerAddress).slice(0, 3)"
              :key="address"
              class="flex justify-between items-center p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded"
            >
              <div class="flex items-center gap-2">
                <RuiIcon
                  name="wallet-3-line"
                  class="text-rui-primary"
                  size="20"
                />
                <HashLink
                  :text="address"
                  chain="ethereum"
                  class="font-mono text-sm"
                />
              </div>
              <span class="font-semibold">{{ gas }} {{ t('staking.eth2') }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="hasSectionData(summary.transactionsPerChain)"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <RuiIcon
              name="git-branch-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.transactions_by_chain') }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="(count, chain) in summary.transactionsPerChain"
              :key="chain"
              class="flex justify-between items-center p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded"
            >
              <div class="flex items-center gap-2">
                <LocationIcon
                  :item="chain.toLowerCase().replace(/_/g, '-')"
                  :icon="true"
                  size="24px"
                />
                <span>{{ getChainName(chain.toLowerCase().replace(/_/g, '-')) }}</span>
              </div>
              <span class="font-semibold">{{ count }} {{ t('explorers.tx') }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="hasSectionData(summary.transactionsPerProtocol)"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <RuiIcon
              name="apps-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.protocol_activity') }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="protocolData in summary.transactionsPerProtocol.slice(0, 3)"
              :key="protocolData.protocol"
              class="flex justify-between items-center p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded"
            >
              <div class="flex items-center gap-2">
                <CounterpartyDisplay :counterparty="protocolData.protocol" />
              </div>
              <span class="font-semibold">{{ protocolData.transactions }} {{ t('explorers.tx') }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="hasSectionData(summary.tradesByExchange)"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <RuiIcon
              name="exchange-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.exchange_activity') }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="[exchange, count] in Object.entries(summary.tradesByExchange).slice(0, 3)"
              :key="exchange"
              class="flex justify-between items-center p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded"
            >
              <div class="flex items-center gap-2">
                <LocationIcon
                  :item="exchange.toLowerCase()"
                  size="24px"
                  :icon="true"
                />
                <span>{{ exchange }}</span>
              </div>
              <span class="font-semibold">{{ count }} {{ t('import_data.bisq.import_trade') }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="showGnosisData && hasSectionData(summary.gnosisMaxPaymentsByCurrency)"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <AppImage
              src="./assets/images/services/gnosispay.png"
              width="24px"
              height="24px"
              contain
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.gnosis_payments') }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="info in currencyDisplayInfo.slice(0, 3)"
              :key="info.code"
              class="flex justify-between items-center p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded"
            >
              <div class="flex items-center gap-2">
                <span class="text-xl">{{ info.symbol }}</span>
                <span class="font-medium">{{ info.name }}</span>
              </div>
              <div class="flex items-center gap-2">
                <AmountDisplay
                  :value="bigNumberify(info.amount)"
                  :integer="false"
                  :floating-precision="2"
                  show-currency="none"
                  class="font-semibold"
                />
                <span class="text-sm text-rui-text-secondary">{{ info.code }}</span>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="hasSectionData(summary.topDaysByNumberOfTransactions)"
          class="p-6 rounded-lg bg-white dark:bg-rui-grey-900 border border-rui-grey-300 dark:border-rui-grey-800"
        >
          <div class="flex items-center gap-2 mb-4">
            <RuiIcon
              name="calendar-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.top_days') }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="(day, index) in summary.topDaysByNumberOfTransactions.slice(0, 3)"
              :key="day.timestamp"
              class="flex justify-between items-center p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded"
            >
              <div class="flex items-center gap-2">
                <span class="text-xl font-medium text-rui-primary">#{{ index + 1 }}</span>
                <span>{{ formatDate(day.timestamp) }}</span>
              </div>
              <span class="font-semibold">{{ day.amount }} {{ t('explorers.tx') }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </BigDialog>
</template>
