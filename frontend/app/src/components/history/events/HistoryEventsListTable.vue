<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import Fragment from '@/components/helper/Fragment';
import { type HistoryEventEntry } from '@/types/history/events';
import { isEvmEvent } from '@/utils/history/events';

type DeleteEvent = {
  canDelete: boolean;
  item: HistoryEventEntry;
};

const props = withDefaults(
  defineProps<{
    events: HistoryEventEntry[];
    blockNumber?: number;
    loading?: boolean;
  }>(),
  {
    loading: false,
    blockNumber: undefined
  }
);

const emit = defineEmits<{
  (e: 'edit:event', data: HistoryEventEntry): void;
  (e: 'delete:event', data: DeleteEvent): void;
  (e: 'show:missing-rule-action', data: HistoryEventEntry): void;
}>();

const { t } = useI18n();
const { getChain } = useSupportedChains();
const isNoTxHash = (item: HistoryEventEntry) =>
  item.entryType === HistoryEventEntryType.EVM_EVENT &&
  ((item.counterparty === 'eth2' && item.eventSubtype === 'deposit asset') ||
    (item.counterparty === 'gitcoin' && item.eventSubtype === 'apply') ||
    item.counterparty === 'safe-multisig');

const editEvent = (item: HistoryEventEntry) => emit('edit:event', item);
const deleteEvent = (item: HistoryEventEntry) =>
  emit('delete:event', {
    item,
    canDelete: isEvmEvent(item) ? props.events.length > 1 : true
  });
</script>

<template>
  <Fragment>
    <template v-if="events.length > 0">
      <div
        v-for="(item, index) in events"
        :key="index"
        class="grid md:grid-cols-4 gap-x-2 gap-y-4 lg:grid-cols-[repeat(20,minmax(0,1fr))] py-4 items-center"
        :class="{
          'border-b border-default': index < events.length - 1
        }"
      >
        <HistoryEventType
          :event="item"
          :chain="getChain(item.location)"
          class="md:col-span-2 lg:col-span-6"
        />
        <HistoryEventAsset :event="item" class="md:col-span-2 lg:col-span-4" />
        <HistoryEventNote
          v-bind="item"
          :amount="item.balance.amount"
          :chain="getChain(item.location)"
          :no-tx-hash="isNoTxHash(item)"
          :block-number="blockNumber"
          class="break-words leading-6 md:col-span-3 lg:col-span-7"
        />
        <RowActions
          class="lg:col-span-3"
          align="end"
          :delete-tooltip="t('transactions.events.actions.delete')"
          :edit-tooltip="t('transactions.events.actions.edit')"
          @edit-click="editEvent(item)"
          @delete-click="deleteEvent(item)"
        >
          <RuiTooltip
            v-if="item.missingAccountingRule"
            :popper="{ placement: 'top', offsetDistance: 0 }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                variant="text"
                color="warning"
                icon
                @click="emit('show:missing-rule-action', item)"
              >
                <RuiIcon size="16" name="information-line" />
              </RuiButton>
            </template>
            {{ t('actions.history_events.missing_rule.title') }}
          </RuiTooltip>
        </RowActions>
      </div>
    </template>

    <template v-else>
      <div v-if="loading">
        {{ t('transactions.events.loading') }}
      </div>
      <div v-else>
        {{ t('transactions.events.no_data') }}
      </div>
    </template>
  </Fragment>
</template>
