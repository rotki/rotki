<script setup lang="ts">
import type { TxQueryStatusData } from '@/store/history/query-status/tx-query-status';
import type {
  EvmUnDecodedTransactionsData,
  HistoryEventsQueryData,
} from '@/types/websocket-messages';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import EventDecodingStatusDetails from '@/components/history/events/EventDecodingStatusDetails.vue';
import HistoryEventsQueryStatus from '@/components/history/events/query-status/HistoryEventsQueryStatus.vue';
import TransactionQueryStatus from '@/components/history/events/tx/query-status/TransactionQueryStatus.vue';
import { useRefWithDebounce } from '@/composables/ref';

interface HistoryQueryStatusDialogProps {
  onlyChains?: string[];
  locations?: string[];
  transactions?: TxQueryStatusData[];
  decodingStatus: EvmUnDecodedTransactionsData[];
  events?: HistoryEventsQueryData[];
  getKey: (item: TxQueryStatusData | HistoryEventsQueryData) => string;
  loading: boolean;
}

const props = withDefaults(defineProps<HistoryQueryStatusDialogProps>(), {
  events: () => [],
  locations: () => [],
  onlyChains: () => [],
  transactions: () => [],
});

const { t } = useI18n({ useScope: 'global' });

const { loading } = toRefs(props);

const usedLoading = useRefWithDebounce(loading, 500);
</script>

<template>
  <RuiDialog max-width="1200">
    <template #activator="{ attrs }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="ml-4"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            class="mt-1"
            size="sm"
            v-bind="attrs"
          >
            <RuiIcon name="lu-info" />
          </RuiButton>
        </template>
        {{ t('common.details') }}
      </RuiTooltip>
    </template>
    <template #default="{ close }">
      <RuiCard>
        <template #custom-header>
          <div class="flex justify-between gap-4 px-4 py-2 items-center border-b border-default">
            <h5 class="text-h6 text-rui-text">
              {{ t('transactions.query_all.modal_title') }}
            </h5>
            <RuiButton
              icon
              variant="text"
              @click="close()"
            >
              <RuiIcon name="lu-x" />
            </RuiButton>
          </div>
        </template>

        <div :class="$style.content">
          <HistoryEventsQueryStatus
            :locations="locations"
            :events="events"
          />
          <TransactionQueryStatus
            :query-statuses="transactions"
            :only-chains="onlyChains"
          />

          <RuiDivider class="-my-2" />

          <div>
            <h6 class="text-body-1 font-medium mb-2">
              {{ t('transactions.events_decoding.title') }}
            </h6>
            <template v-if="decodingStatus.length > 0">
              <EventDecodingStatusDetails
                v-for="item in decodingStatus"
                :key="item.chain"
                class="py-1"
                :item="item"
              />
            </template>
            <template v-else-if="usedLoading">
              <div class="flex gap-2 text-sm">
                <RuiIcon
                  color="primary"
                  name="lu-hourglass"
                  size="22"
                />
                {{ t('transactions.events_decoding.decoded.not_started') }}
              </div>
            </template>
            <template v-else>
              <div class="flex gap-2 text-sm">
                <SuccessDisplay
                  success
                  size="22"
                />
                {{ t('transactions.events_decoding.decoded.true') }}
              </div>
            </template>
          </div>
        </div>
        <template #footer>
          <div class="w-full" />
          <RuiButton
            color="primary"
            @click="close()"
          >
            {{ t('common.actions.close') }}
          </RuiButton>
        </template>
      </RuiCard>
    </template>
  </RuiDialog>
</template>

<style module lang="scss">
.content {
  @apply overflow-y-auto -mx-4 px-4 pb-4 flex flex-col gap-8;
  max-height: calc(90vh - 11.875rem);
  min-height: 50vh;

}
</style>
