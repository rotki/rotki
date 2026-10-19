<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import HistoryRefreshBanks from '@/modules/history/refresh/HistoryRefreshBanks.vue';
import HistoryRefreshChains from '@/modules/history/refresh/HistoryRefreshChains.vue';
import HistoryRefreshExchanges from '@/modules/history/refresh/HistoryRefreshExchanges.vue';
import HistoryRefreshProtocolEvents from '@/modules/history/refresh/HistoryRefreshProtocolEvents.vue';
import HistoryRefreshStakingEvents from '@/modules/history/refresh/HistoryRefreshStakingEvents.vue';
import { HistoryRefreshTab, useHistoryRefreshSelection } from '@/modules/history/refresh/use-history-refresh-selection';

const {
  processing,
  disabled = false,
} = defineProps<{
  processing: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  refresh: [payload?: HistoryRefreshEventData];
  repull: [];
}>();

const open = ref<boolean>(false);

const chains = useTemplateRef<ComponentExposed<typeof HistoryRefreshChains>>('chains');
const exchanges = useTemplateRef<ComponentExposed<typeof HistoryRefreshExchanges>>('exchanges');
const banks = useTemplateRef<ComponentExposed<typeof HistoryRefreshBanks>>('banks');
const validatorEvents = useTemplateRef<ComponentExposed<typeof HistoryRefreshStakingEvents>>('validatorEvents');
const protocols = useTemplateRef<ComponentExposed<typeof HistoryRefreshProtocolEvents>>('protocols');

const { t } = useI18n({ useScope: 'global' });

const {
  getRefreshPayload,
  indeterminate,
  modelSearch,
  modelSelectedAccounts,
  modelSelectedBanks,
  modelSelectedChain,
  modelSelectedExchanges,
  modelSelectedProtocolQueries,
  modelSelectedQueries,
  modelTab,
  reset,
  searchLabel,
  selected,
  setAllSelected,
  totalSelected,
  typeText,
} = useHistoryRefreshSelection();

function refresh(): void {
  emit('refresh', getRefreshPayload());
  reset();
  set(open, false);
}

function repull(): void {
  emit('repull');
  reset();
  set(open, false);
}

function toggleSelectAll(): void {
  const tabs: Record<HistoryRefreshTab, { toggleSelectAll: () => void } | null> = {
    [HistoryRefreshTab.BANKS]: get(banks),
    [HistoryRefreshTab.CHAINS]: get(chains),
    [HistoryRefreshTab.EVENTS]: get(validatorEvents),
    [HistoryRefreshTab.EXCHANGES]: get(exchanges),
    [HistoryRefreshTab.PROTOCOLS]: get(protocols),
  };

  tabs[get(modelTab)]?.toggleSelectAll();
}
</script>

<template>
  <RuiMenu
    v-model="open"
    :options="{ offset: { crossAxis: 35 }, placement: 'bottom' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        color="primary"
        class="h-9 px-2.5"
        :disabled="disabled"
        :aria-label="t('common.actions.more')"
        data-testid="refresh-selection-toggle"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-chevron-down"
          size="16"
        />
      </RuiButton>
    </template>

    <div class="w-112.5">
      <div class="p-4 border-b border-default">
        <RuiTextField
          v-model="modelSearch"
          data-testid="refresh-selection-search"
          dense
          color="primary"
          :label="searchLabel"
          prepend-icon="lu-search"
          hide-details
          clearable
        />
      </div>
      <RuiTabs v-model="modelTab">
        <RuiTab :value="HistoryRefreshTab.CHAINS">
          {{ t('history_refresh_selection.tabs.chains') }}
        </RuiTab>
        <RuiTab :value="HistoryRefreshTab.EXCHANGES">
          {{ t('history_refresh_selection.tabs.exchanges') }}
        </RuiTab>
        <RuiTab :value="HistoryRefreshTab.BANKS">
          {{ t('history_refresh_selection.tabs.banks') }}
        </RuiTab>
        <RuiTab :value="HistoryRefreshTab.EVENTS">
          {{ t('history_refresh_selection.tabs.events') }}
        </RuiTab>
        <RuiTab :value="HistoryRefreshTab.PROTOCOLS">
          {{ t('history_refresh_selection.tabs.protocols') }}
        </RuiTab>
      </RuiTabs>

      <div class="px-4 py-2 text-xs font-medium uppercase border-y border-default bg-rui-grey-50 dark:bg-rui-grey-900">
        {{ t('history_refresh_selection.selection') }}
      </div>

      <RuiTabItems v-model="modelTab">
        <RuiTabItem :value="HistoryRefreshTab.CHAINS">
          <HistoryRefreshChains
            ref="chains"
            v-model:search="modelSearch"
            v-model:chain="modelSelectedChain"
            v-model="modelSelectedAccounts"
            :processing="processing"
            @update:all-selected="setAllSelected('chains', $event)"
          />
        </RuiTabItem>
        <RuiTabItem :value="HistoryRefreshTab.EXCHANGES">
          <HistoryRefreshExchanges
            ref="exchanges"
            v-model:search="modelSearch"
            v-model="modelSelectedExchanges"
            :processing="processing"
            @update:all-selected="setAllSelected('exchanges', $event)"
          />
        </RuiTabItem>
        <RuiTabItem :value="HistoryRefreshTab.BANKS">
          <HistoryRefreshBanks
            ref="banks"
            v-model:search="modelSearch"
            v-model="modelSelectedBanks"
            :processing="processing"
            @update:all-selected="setAllSelected('banks', $event)"
          />
        </RuiTabItem>
        <RuiTabItem :value="HistoryRefreshTab.EVENTS">
          <HistoryRefreshStakingEvents
            ref="validatorEvents"
            v-model="modelSelectedQueries"
            v-model:search="modelSearch"
            :processing="processing"
            @update:all-selected="setAllSelected('events', $event)"
          />
        </RuiTabItem>
        <RuiTabItem :value="HistoryRefreshTab.PROTOCOLS">
          <HistoryRefreshProtocolEvents
            ref="protocols"
            v-model="modelSelectedProtocolQueries"
            v-model:search="modelSearch"
            :processing="processing"
            @update:all-selected="setAllSelected('protocols', $event)"
          />
        </RuiTabItem>
      </RuiTabItems>

      <div class="px-4 py-2 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
          data-testid="refresh-selection-select-all"
          :disabled="processing"
          :indeterminate="indeterminate"
          :model-value="selected"
          size="sm"
          hide-details
          @click.prevent="toggleSelectAll()"
        >
          {{ t('common.actions.select_all') }}
        </RuiCheckbox>
        <div class="flex items-center gap-2">
          <RuiButton
            v-if="indeterminate || selected"
            data-testid="refresh-selection-cancel"
            variant="text"
            @click="reset()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            data-testid="refresh-selection-refresh"
            :disabled="!(indeterminate || selected)"
            :loading="processing"
            @click="refresh()"
          >
            {{ t('history_refresh_selection.refresh', { total: totalSelected, type: typeText }) }}
          </RuiButton>
        </div>
      </div>

      <div class="px-4 py-2 border-t border-default">
        <RuiButton
          variant="text"
          size="sm"
          class="w-full justify-start!"
          :disabled="processing"
          data-testid="refresh-selection-repull"
          @click="repull()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-clock-arrow-up"
              size="16"
            />
          </template>
          {{ t('history_refresh_selection.repull') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
