<template>
  <tr v-if="length > 0" :class="$style.tr">
    <td :colspan="colspan" class="py-2">
      <div class="d-flex">
        <div v-if="isAllFinished" class="pr-2">
          <v-btn icon @click="resetQueryStatus">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="pr-2">
          <v-btn
            v-if="length > 1 && !isAllFinished"
            icon
            @click="openStatusDropdown = !openStatusDropdown"
          >
            <v-icon v-if="openStatusDropdown"> mdi-chevron-up </v-icon>
            <v-icon v-else> mdi-chevron-down </v-icon>
          </v-btn>
        </div>
        <div>
          <div
            v-if="isAllFinished || (!openStatusDropdown && length > 1)"
            class="py-2 d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isAllFinished"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="$style['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>
            <div v-if="isAllFinished">
              {{ t('transactions.query_status.done_group', { length }) }}
            </div>
            <div v-else>
              {{
                t('transactions.query_status.group', {
                  length: queryingLength
                })
              }}
            </div>
          </div>
          <div
            v-for="item in sortedQueryStatus"
            v-else
            :key="item.address"
            class="d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isStatusFinished(item)"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="$style['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>

            <i18n
              :path="getItemTranslationKey(item)"
              tag="div"
              class="d-flex py-2 text-no-wrap flex-wrap"
            >
              <template #status>
                {{ getLabel(item) }}
              </template>
              <template #address>
                <div class="font-weight-bold px-1 text-no-wrap">
                  <hash-link :text="item.address" />
                </div>
              </template>
              <template #start>
                <div class="font-weight-bold px-1 text-no-wrap">
                  <date-display :timestamp="item.period[0]" />
                </div>
              </template>
              <template #end>
                <div class="font-weight-bold px-1 text-no-wrap">
                  <date-display :timestamp="item.period[1]" />
                </div>
              </template>
            </i18n>
          </div>
        </div>
        <v-spacer />
        <v-dialog width="1200">
          <template #activator="{ on }">
            <v-btn text class="ml-4" v-on="on">
              {{ t('common.details') }}
              <v-icon small>mdi-chevron-right</v-icon>
            </v-btn>
          </template>
          <template #default="dialog">
            <v-card :class="$style.card">
              <v-card-title class="d-flex justify-space-between pb-0">
                <div>
                  {{ t('transactions.query_status.title') }}
                </div>
                <v-btn icon @click="dialog.value = false">
                  <v-icon>mdi-close</v-icon>
                </v-btn>
              </v-card-title>

              <div class="px-6 pb-4 text-caption">
                <div v-if="isAllFinished">
                  {{ t('transactions.query_status.done_group', { length }) }}
                </div>
                <div v-else>
                  {{
                    t('transactions.query_status.group', {
                      length: queryingLength
                    })
                  }}
                </div>
              </div>

              <div class="px-6 pb-4">
                <div
                  v-for="item in queryStatus"
                  :key="item.address"
                  :class="$style.item"
                >
                  <div class="d-flex">
                    <i18n
                      :path="getItemTranslationKey(item)"
                      tag="div"
                      class="d-flex py-2 text-no-wrap flex-wrap"
                      :class="isStatusFinished(item) ? 'green--text' : ''"
                    >
                      <template #status>
                        {{ getLabel(item) }}
                      </template>
                      <template #address>
                        <div class="font-weight-bold px-1 text-no-wrap">
                          <hash-link :text="item.address" />
                        </div>
                      </template>
                      <template #start>
                        <div class="font-weight-bold px-1 text-no-wrap">
                          <date-display :timestamp="item.period[0]" />
                        </div>
                      </template>
                      <template #end>
                        <div class="font-weight-bold px-1 text-no-wrap">
                          <date-display :timestamp="item.period[1]" />
                        </div>
                      </template>
                    </i18n>

                    <v-tooltip bottom>
                      <template #activator="{ on }">
                        <v-icon class="ml-2" v-on="on">
                          mdi-help-circle
                        </v-icon>
                      </template>
                      <i18n
                        :path="
                          item.period[0] === 0
                            ? 'transactions.query_status.latest_period_end_date'
                            : 'transactions.query_status.latest_period_date_range'
                        "
                      >
                        <template #start>
                          <date-display :timestamp="item.period[0]" />
                        </template>
                        <template #end>
                          <date-display :timestamp="item.period[1]" />
                        </template>
                      </i18n>
                    </v-tooltip>
                  </div>
                  <v-stepper vertical flat :value="-1" :class="$style.stepper">
                    <v-stepper-header :class="$style['stepper__header']">
                      <template v-for="(step, index) in steps">
                        <v-stepper-step
                          :key="step"
                          :class="$style['stepper__item']"
                          :step="index + 1"
                          color="green"
                          :complete="isStepCompleted(item, index)"
                        >
                          <div
                            :class="
                              isStepCompleted(item, index) ? 'green--text' : ''
                            "
                          >
                            {{ step }}
                          </div>
                          <v-progress-circular
                            v-if="isStepInProgress(item, index)"
                            :class="$style['stepper__progress']"
                            size="32"
                            indeterminate
                            width="2"
                            color="primary"
                          />
                        </v-stepper-step>
                      </template>
                    </v-stepper-header>
                  </v-stepper>
                </div>
              </div>
            </v-card>
          </template>
        </v-dialog>
      </div>
    </td>
  </tr>
</template>
<script setup lang="ts">
import { useTxQueryStatus } from '@/store/history/query-status';
import {
  EthereumTransactionQueryData,
  EthereumTransactionsQueryStatus
} from '@/types/websocket-messages';
import { toSentenceCase } from '@/utils/text';

defineProps({
  colspan: { required: true, type: Number }
});

const { t, tc } = useI18n();

const statusesData = {
  [EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: {
    index: -1
  },
  [EthereumTransactionsQueryStatus.ACCOUNT_CHANGE]: {
    index: 0
  },
  [EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS]: {
    index: 1,
    label: tc('transactions.query_status.statuses.querying_transactions')
  },
  [EthereumTransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: {
    index: 2,
    label: tc(
      'transactions.query_status.statuses.querying_internal_transactions'
    )
  },
  [EthereumTransactionsQueryStatus.QUERYING_ETHEREUM_TOKENS_TRANSACTIONS]: {
    index: 3,
    label: tc(
      'transactions.query_status.statuses.querying_ethereum_tokens_transactions'
    )
  },
  [EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: {
    index: 4
  }
};

const steps = [
  toSentenceCase(
    tc('transactions.query_status.statuses.querying_transactions')
  ),
  toSentenceCase(
    tc('transactions.query_status.statuses.querying_internal_transactions')
  ),
  toSentenceCase(
    tc(
      'transactions.query_status.statuses.querying_ethereum_tokens_transactions'
    )
  )
];

const openStatusDropdown = ref<boolean>(false);

const transactionsQueryStatusStore = useTxQueryStatus();
const { queryStatus } = toRefs(transactionsQueryStatusStore);

const { resetQueryStatus } = transactionsQueryStatusStore;

const isQueryStatusRange = (data: EthereumTransactionQueryData) => {
  return data.period?.[0] > 0;
};

const getStatusData = (data: EthereumTransactionQueryData) => {
  return statusesData[data.status];
};

const getLabel = (data: EthereumTransactionQueryData) => {
  const statusData = getStatusData(data);
  if ('label' in statusData) {
    return statusData.label;
  }

  return '';
};

const isStatusFinished = (item: EthereumTransactionQueryData) => {
  return (
    item.status ===
    EthereumTransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED
  );
};

const isAllFinished = computed<boolean>(() => {
  const queryStatusVal = get(queryStatus);
  const addresses = Object.keys(queryStatusVal);

  return addresses.every((address: string) => {
    return isStatusFinished(queryStatusVal[address]);
  });
});

const getItemTranslationKey = (item: EthereumTransactionQueryData) => {
  const isRange = isQueryStatusRange(item);

  if (isStatusFinished(item)) {
    return isRange
      ? 'transactions.query_status.done_date_range'
      : 'transactions.query_status.done_end_date';
  }

  return isRange
    ? 'transactions.query_status.date_range'
    : 'transactions.query_status.end_date';
};

const isStepCompleted = (
  item: EthereumTransactionQueryData,
  stepIndex: number
) => {
  return getStatusData(item).index > stepIndex + 1;
};

const isStepInProgress = (
  item: EthereumTransactionQueryData,
  stepIndex: number
) => {
  return getStatusData(item).index === stepIndex + 1;
};

const sortedQueryStatus = computed<EthereumTransactionQueryData[]>(() => {
  const statuses = Object.values(get(queryStatus));

  return statuses.sort(
    (a: EthereumTransactionQueryData, b: EthereumTransactionQueryData) =>
      (isStatusFinished(a) ? 1 : 0) - (isStatusFinished(b) ? 1 : 0)
  );
});

const length = computed<number>(() => Object.keys(get(queryStatus)).length);

const queryingLength = computed<number>(
  () =>
    Object.values(get(queryStatus)).filter(item => !isStatusFinished(item))
      .length
);
</script>
<style module lang="scss">
.tr {
  background: transparent !important;
}

.row {
  display: flex;
}

.item {
  padding: 1rem 0;
  border-top: 1px solid var(--v-rotki-light-grey-darken1);
}

.card {
  width: 100%;
  overflow: auto;
}

.check-icon {
  margin: -2px;
}

.stepper {
  padding-bottom: 0;

  &__header {
    box-shadow: none;
    justify-content: flex-start;
    height: auto;
    padding-left: 0.5rem;

    @media (max-width: 900px) {
      flex-direction: column;
    }
  }

  &__item {
    padding: 0.5rem 1.5rem 0.5rem 0 !important;
  }

  &__progress {
    position: absolute;
    left: -4px;
    top: 50%;
    transform: translateY(-50%);
  }
}
</style>
