<script setup lang="ts">
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import EventDecodingStatusDetails from '@/components/history/events/EventDecodingStatusDetails.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { usePremium } from '@/composables/premium';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { useStatusStore } from '@/store/status';
import { useCurrencies } from '@/types/currencies';
import LocationIcon from '../history/LocationIcon.vue';
import ProgressScreen from '../helper/ProgressScreen.vue';
import HashLink from '../helper/HashLink.vue';
import AppImage from '../common/AppImage.vue';
import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';

interface TransactionDay {
  date: string;
  count: number;
}

interface WrappedSummary {
  ethGasSpent: string;
  ethGasPerAddress: Record<string, string>;
  tradesByExchange: Record<string, number>;
  transactionsByChain: Record<string, number>;
  gnosisMaxPayments: Record<string, string>;
  topTransactionDays: TransactionDay[];
  transactionsByProtocol: Record<string, number>;
  decodingStatus: EvmUnDecodedTransactionsData[];
}

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

const gnosisPayKey = computed(() => apiKey('gnosis_pay'));
const showGnosisData = computed(() => get(premium) && gnosisPayKey.value);

const loading = ref(false);
const summary = ref<WrappedSummary | null>(null);
const loadingProgress = ref('0');

const isDecoding = computed(() => get(isTaskRunning(TaskType.TRANSACTIONS_DECODING)));
const sectionLoading = computed(() => isSectionLoading(Section.HISTORY_EVENT));
const refreshing = logicOr(sectionLoading, isDecoding);

const allEventsDecoded = computed(() => {
  if (!summary.value?.decodingStatus)
    return false;
  return summary.value.decodingStatus.every(status =>
    status.processed === status.total,
  );
});

const { findCurrency } = useCurrencies();

const currencyDisplayInfo = computed(() => {
  if (!summary.value?.gnosisMaxPayments)
    return [];

  return Object.entries(summary.value.gnosisMaxPayments).map(([code, amount]) => {
    const currency = findCurrency(code);
    return {
      amount,
      code,
      name: currency.name,
      symbol: currency.unicodeSymbol,
    };
  });
});

async function fetchData() {
  if (!get(premium) || loading.value)
    return;

  try {
    loading.value = true;
    loadingProgress.value = '0';

    const progressInterval = setInterval(() => {
      const current = Number(loadingProgress.value);
      if (current < 90) {
        loadingProgress.value = (current + 10).toString();
      }
    }, 500);

    summary.value = {
      decodingStatus: [
        { chain: 'ethereum', processed: 100, total: 100 },
        { chain: 'polygon_pos', processed: 95, total: 100 },
      ],
      ethGasPerAddress: {
        '0x09A6...44a74242Ce': '0.45',
        '0x09A6...44a74243Ce': '0.38',
        '0x09A6...44a74244Ce': '0.40',
      },
      ethGasSpent: '1.23',
      gnosisMaxPayments: {
        EUR: '4200',
        GBP: '3600',
        USD: '5000',
      },
      topTransactionDays: [
        { count: 25, date: '2024-01-22' },
        { count: 20, date: '2024-05-01' },
        { count: 18, date: '2024-11-10' },
      ],
      tradesByExchange: {
        binance: 22,
        bybit: 99,
        kraken: 193,
      },
      transactionsByChain: {
        ethereum: 1256,
        optimism: 734,
        polygon_pos: 272,
      },
      transactionsByProtocol: {
        cow_swap: 30,
        makerdao_dsr: 15,
        uniswap: 20,
      },
    };

    loadingProgress.value = '100';
    clearInterval(progressInterval);
  }
  catch (error) {
    console.error('Error fetching wrapped data:', error);
    summary.value = null;
  }
  finally {
    loading.value = false;
  }
}

function hasSectionData(data: Record<string, any> | undefined): boolean {
  return !!data && Object.keys(data).length > 0;
}

function closeDialog() {
  emit('update:display', false);
  emit('close');
}

watch(() => props.display, async (newVal) => {
  if (newVal && !summary.value) {
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
            {{ t('wrapped.loading') }}
          </template>
          {{ t('wrapped.loading_description') }}
        </ProgressScreen>
      </div>
      <div v-else>
        <RuiAlert
          v-if="refreshing"
          type="info"
          class="mb-4"
        >
          {{ t('transactions.events_decoding.progress') }}
        </RuiAlert>

        <div
          v-if="summary?.decodingStatus"
          class="mb-6"
        >
          <div
            v-if="allEventsDecoded"
            class="flex gap-2 mb-4"
          >
            <SuccessDisplay
              success
              size="22"
            />
            {{ t('transactions.events_decoding.decoded.true') }}
          </div>
          <template v-else>
            <EventDecodingStatusDetails
              v-for="item in summary.decodingStatus"
              :key="item.chain"
              class="mb-4"
              :item="item"
            />
          </template>
        </div>

        <div
          v-if="summary"
          class="flex flex-col gap-8"
        >
          <div class="py-8 w-full rounded-lg flex flex-col items-center bg-gradient-to-br from-rui-primary/5 to-rui-primary/10 dark:from-rui-primary-darker/5 dark:to-rui-primary-darker/10">
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

          <div class="rounded-lg bg-gradient-to-br from-rui-primary/[0.02] to-transparent dark:from-rui-primary-darker/[0.02]">
            <h3 class="text-lg font-medium p-6 pb-4 flex items-center gap-2">
              <RuiIcon
                name="gas-station-line"
                class="text-rui-primary"
                size="24"
              />
              {{ t('wrapped.gas_spent') }}
            </h3>
            <div class="px-6 pb-6">
              <div class="text-xl font-bold mb-6 bg-gradient-to-r from-rui-primary to-rui-primary-dark dark:from-rui-primary-darker dark:to-rui-primary bg-clip-text text-transparent">
                {{ summary.ethGasSpent }}
              </div>
              <div class="flex flex-col gap-3">
                <div
                  v-for="(gas, address) in summary.ethGasPerAddress"
                  :key="address"
                  class="flex justify-between items-center p-4 bg-white dark:bg-rui-grey-900 rounded-lg border border-rui-grey-200 dark:border-rui-grey-700"
                >
                  <div class="flex items-center gap-3">
                    <RuiIcon
                      name="wallet-3-line"
                      size="20"
                      class="text-rui-primary"
                    />
                    <HashLink
                      :text="address"
                      chain="ethereum"
                      class="font-mono text-sm"
                    />
                  </div>
                  <span class="font-semibold">{{ gas }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-lg bg-gradient-to-br from-rui-primary/[0.02] to-transparent dark:from-rui-primary-darker/[0.02]">
            <h3 class="text-lg font-medium p-6 pb-4 flex items-center gap-2">
              <RuiIcon
                name="exchange-line"
                class="text-rui-primary"
                size="24"
              />
              {{ t('wrapped.exchange_activity') }}
            </h3>
            <div class="px-6 pb-6">
              <div class="flex flex-col gap-3">
                <div
                  v-for="(count, exchange) in summary.tradesByExchange"
                  :key="exchange"
                  class="flex justify-between items-center p-4 bg-white dark:bg-rui-grey-900 rounded-lg border border-rui-grey-200 dark:border-rui-grey-700"
                >
                  <div class="flex items-center gap-3">
                    <LocationIcon
                      :item="exchange"
                      size="24px"
                      :icon="true"
                    />
                    <span class="font-medium capitalize">{{ exchange }}</span>
                  </div>
                  <span class="font-semibold">{{ count }} {{ t('import_data.bisq.import_trade') }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="p-6 pb-4 flex items-center gap-2 border-b border-rui-grey-200 dark:border-rui-grey-700">
            <RuiIcon
              name="git-branch-line"
              class="text-rui-primary"
              size="24"
            />
            <h3 class="text-lg font-medium">
              {{ t('wrapped.transactions_by_chain') }}
            </h3>
          </div>
          <div class="px-6 pb-6">
            <div class="flex flex-col gap-3">
              <div
                v-for="(count, chain) in summary.transactionsByChain"
                :key="chain"
                class="flex justify-between items-center p-4 bg-white dark:bg-rui-grey-900 rounded-lg border border-rui-grey-200 dark:border-rui-grey-700"
              >
                <div class="flex items-center gap-3">
                  <LocationIcon
                    :item="chain"
                    :icon="true"
                    size="24px"
                  />
                  <span class="font-medium capitalize">{{ chain.replace('_', ' ') }}</span>
                </div>
                <span class="font-semibold">{{ count }} {{ t('explorers.tx') }}</span>
              </div>
            </div>
          </div>

          <div class="rounded-lg bg-gradient-to-br from-rui-primary/[0.02] to-transparent dark:from-rui-primary-darker/[0.02]">
            <h3 class="text-lg font-medium p-6 pb-4 flex items-center gap-2">
              <RuiIcon
                name="apps-line"
                class="text-rui-primary"
                size="24"
              />
              {{ t('wrapped.protocol_activity') }}
            </h3>
            <div class="px-6 pb-6">
              <div class="flex flex-col gap-3">
                <div
                  v-for="(count, protocol) in summary.transactionsByProtocol"
                  :key="protocol"
                  class="flex justify-between items-center p-4 bg-white dark:bg-rui-grey-900 rounded-lg border border-rui-grey-200 dark:border-rui-grey-700"
                >
                  <div class="flex items-center gap-3">
                    <LocationIcon
                      :item="protocol"
                      size="24px"
                      :icon="true"
                    />
                    <span class="font-medium capitalize">{{ protocol.replace('_', ' ') }}</span>
                  </div>
                  <span class="font-semibold">{{ count }} {{ t('explorers.tx') }}</span>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="showGnosisData && hasSectionData(summary.gnosisMaxPayments)"
            class="rounded-lg bg-gradient-to-br from-rui-primary/[0.02] to-transparent dark:from-rui-primary-darker/[0.02]"
          >
            <h3 class="text-lg font-medium p-6 pb-4 flex items-center gap-2">
              <AppImage
                src="./assets/images/services/gnosispay.png"
                width="24px"
                height="24px"
                contain
              />
              {{ t('wrapped.gnosis_payments') }}
            </h3>
            <div class="px-6 pb-6">
              <div class="flex flex-col gap-3">
                <div
                  v-for="info in currencyDisplayInfo"
                  :key="info.code"
                  class="flex items-center justify-between p-4 bg-white dark:bg-rui-grey-900 rounded-lg border border-rui-grey-200 dark:border-rui-grey-700"
                >
                  <div class="flex items-center gap-3">
                    <span class="text-xl font-bold text-rui-primary">
                      {{ info.symbol }}
                    </span>
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
          </div>

          <div
            v-if="summary.topTransactionDays?.length"
            class="rounded-lg bg-gradient-to-br from-rui-primary/[0.02] to-transparent dark:from-rui-primary-darker/[0.02]"
          >
            <h3 class="text-lg font-medium p-6 pb-4 flex items-center gap-2">
              <RuiIcon
                name="calendar-line"
                class="text-rui-primary"
                size="24"
              />
              {{ t('wrapped.top_days') }}
            </h3>
            <div class="px-6 pb-6">
              <div class="flex flex-col">
                <div
                  v-for="(day, index) in summary.topTransactionDays"
                  :key="day.date"
                  class="flex justify-between items-center p-4 bg-white dark:bg-rui-grey-900 rounded-lg border border-rui-grey-200 dark:border-rui-grey-700"
                >
                  <div class="flex items-center gap-4">
                    <div class="flex items-center justify-center w-10 h-10 text-lg font-bold text-rui-primary bg-rui-primary/10 dark:bg-rui-primary-darker/10 rounded-full">
                      #{{ index + 1 }}
                    </div>
                    <div class="flex flex-col">
                      <span class="font-medium">{{ new Date(day.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric' }) }}</span>
                    </div>
                  </div>
                  <span class="font-semibold">{{ day.count }} {{ t('explorers.tx') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </BigDialog>
</template>
