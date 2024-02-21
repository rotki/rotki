<script setup lang="ts">
import type { EvmTransactionQueryData, HistoryEventsQueryData } from '@/types/websocket-messages';
import type { Blockchain } from '@rotki/common/lib/blockchain';

withDefaults(
  defineProps<{
    onlyChains?: Blockchain[];
    locations?: string[];
    transactions?: EvmTransactionQueryData[];
    events?: HistoryEventsQueryData[];
    getKey: (item: EvmTransactionQueryData | HistoryEventsQueryData) => string;
  }>(),
  {
    onlyChains: () => [],
    locations: () => [],
    transactions: () => [],
    events: () => [],
  },
);

const { t } = useI18n();
</script>

<template>
  <VDialog width="1200">
    <template #activator="{ on }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="ml-4"
      >
        <template #activator>
          <RuiButton
            variant="text"
            v-on="on"
          >
            <template #append>
              <RuiIcon name="information-line" />
            </template>
          </RuiButton>
        </template>
        {{ t('common.details') }}
      </RuiTooltip>
    </template>
    <template #default="dialog">
      <RuiCard>
        <template #custom-header>
          <div class="flex justify-between gap-4 p-4 items-center border-b border-default ">
            <div>
              <h5 class="text-h5">
                {{ t('transactions.query_all.modal_title') }}
              </h5>
            </div>
            <RuiButton
              icon
              variant="text"
              @click="dialog.value = false"
            >
              <RuiIcon name="close-line" />
            </RuiButton>
          </div>
        </template>

        <div>
          <h6 class="text-body-1 font-medium">
            {{ t('transactions.query_status_events.title') }}
          </h6>
          <HistoryEventsQueryStatusCurrent
            :locations="locations"
            class="text-subtitle-2 text-rui-text-secondary mt-2"
          />
          <div
            v-for="item in events"
            :key="getKey(item)"
            class="py-1"
          >
            <HistoryEventsQueryStatusDetails :item="item" />
          </div>
        </div>

        <div class="mt-4">
          <h6 class="text-body-1 font-medium">
            {{ t('transactions.query_status.title') }}
          </h6>
          <TransactionQueryStatusCurrent
            :only-chains="onlyChains"
            class="text-subtitle-2 text-rui-text-secondary mt-2"
          />
          <div
            v-for="item in transactions"
            :key="getKey(item)"
            class="py-1"
          >
            <TransactionQueryStatusDetails :item="item" />
            <TransactionQueryStatusSteps :item="item" />
          </div>
        </div>
        <template #footer>
          <div class="w-full" />
          <RuiButton
            color="primary"
            @click="dialog.value = false"
          >
            {{ t('common.actions.close') }}
          </RuiButton>
        </template>
      </RuiCard>
    </template>
  </VDialog>
</template>
