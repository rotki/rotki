<script lang="ts" setup>
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import type { SelectionState } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import HistoryEventsExport from '@/components/history/events/HistoryEventsExport.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useSupportedChains } from '@/composables/info/chains';
import HistoryRedecodeButton from '@/modules/history/redecode/HistoryRedecodeButton.vue';
import { type MatchedKeywordWithBehaviour, SavedFilterLocation, type SearchMatcher } from '@/types/filtering';
import { useRefPropVModel } from '@/utils/model';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const accounts = defineModel<BlockchainAccount<AddressData>[]>('accounts', { required: true });

const toggles = defineModel<HistoryEventsToggles>('toggles', { required: true });

withDefaults(defineProps<{
  matchers: SearchMatcher<any, any>[];
  exportParams: HistoryEventRequestPayload;
  hideAccountSelector?: boolean;
  hideRedecodeButtons?: boolean;
  processing?: boolean;
  selection: SelectionState;
}>(), {
  hideAccountSelector: false,
  hideRedecodeButtons: false,
  processing: false,
});

const emit = defineEmits<{
  'redecode': [payload: 'all' | 'page' | string[]];
  'selection:action': [action: 'toggle-mode' | 'delete' | 'exit' | 'toggle-all'];
}>();

const { t } = useI18n({ useScope: 'global' });

const customizedEventsOnly = useRefPropVModel(toggles, 'customizedEventsOnly');
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');

const { allTxChainsInfo } = useSupportedChains();
const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

// Event handlers
function handleDelete(): void {
  emit('selection:action', 'delete');
}

function handleExit(): void {
  emit('selection:action', 'exit');
}

function handleToggleMode(): void {
  emit('selection:action', 'toggle-mode');
}

function handleToggleAll(): void {
  emit('selection:action', 'toggle-all');
}
</script>

<template>
  <HistoryTableActions hide-divider>
    <template
      v-if="!selection.isActive"
      #filter
    >
      <TableStatusFilter>
        <div class="py-1 max-w-[16rem]">
          <RuiSwitch
            v-model="customizedEventsOnly"
            color="primary"
            class="p-4"
            hide-details
            :label="t('transactions.filter.customized_only')"
          />
          <RuiDivider />
          <RuiSwitch
            v-model="showIgnoredAssets"
            color="primary"
            class="p-4"
            hide-details
            :label="t('transactions.filter.show_ignored_assets')"
          />
          <RuiDivider />
          <RuiSwitch
            v-model="matchExactEvents"
            color="primary"
            class="p-4"
            :label="t('transactions.filter.match_exact_filter')"
            :hint="t('transactions.filter.match_exact_filter_hint')"
          />
        </div>
      </TableStatusFilter>
      <TableFilter
        v-model:matches="filters"
        class="min-w-[12rem] md:min-w-[24rem]"
        :matchers="matchers"
        :location="SavedFilterLocation.HISTORY_EVENTS"
      />
    </template>

    <template v-if="selection.isActive">
      <RuiCheckbox
        :model-value="selection.isAllSelected"
        :indeterminate="selection.isPartiallySelected"
        color="primary"
        hide-details
        class="ml-2 pt-[1px] h-11"
        @update:model-value="handleToggleAll()"
      />
      <span class="text-sm text-rui-text-secondary mr-4 select-none">
        {{ t('transactions.events.selection_mode.selected_count', { count: selection.selectedCount }) }}
      </span>
      <RuiButton
        color="error"
        variant="outlined"
        class="h-10"
        :disabled="selection.selectedCount === 0"
        @click="handleDelete()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="20"
          />
        </template>
        {{ t('transactions.events.selection_mode.delete_selected') }}
      </RuiButton>
      <RuiButton
        variant="text"
        class="h-10"
        @click="handleExit()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
    </template>
    <template v-else>
      <RuiTooltip>
        <template #activator>
          <RuiButton
            variant="text"
            class="!h-10"
            @click="handleToggleMode()"
          >
            <template #prepend>
              <RuiIcon
                class="text-rui-text-secondary"
                name="lu-copy-check"
                size="24"
              />
            </template>
          </RuiButton>
        </template>
        {{ t('transactions.events.selection_mode.tooltip') }}
      </RuiTooltip>

      <HistoryRedecodeButton
        v-if="!hideRedecodeButtons"
        :processing="processing"
        @redecode="emit('redecode', $event)"
      />

      <HistoryEventsExport
        :match-exact-events="toggles.matchExactEvents"
        :filters="exportParams"
      />

      <BlockchainAccountSelector
        v-if="!hideAccountSelector"
        v-model="accounts"
        class="w-[18rem]"
        :chains="txChainIds"
        dense
        :label="t('transactions.filter.account')"
        outlined
        multichain
        hide-chain-icon
        unique
      />
    </template>
  </HistoryTableActions>
</template>
