<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { HistoryRefreshEventData, RefreshChainAddress } from '@/modules/history/refresh/types';
import type { Exchange } from '@/types/exchanges';
import type { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import HistoryRefreshChains from '@/modules/history/refresh/HistoryRefreshChains.vue';
import HistoryRefreshExchanges from '@/modules/history/refresh/HistoryRefreshExchanges.vue';
import HistoryRefreshProtocolEvents from '@/modules/history/refresh/HistoryRefreshProtocolEvents.vue';
import HistoryRefreshStakingEvents from '@/modules/history/refresh/HistoryRefreshStakingEvents.vue';

withDefaults(defineProps<{
  processing: boolean;
  disabled?: boolean;
}>(), {
  disabled: false,
});

const emit = defineEmits<{
  refresh: [payload?: HistoryRefreshEventData];
}>();

const open = ref<boolean>(false);
const search = ref<string>('');
const tab = ref<'chains' | 'exchanges' | 'events' | 'protocols'>('chains');

const selectedAccounts = ref<RefreshChainAddress[]>([]);
const allAccountsSelected = ref<boolean>(false);
const selectedChain = ref<string>();

const selectedExchanges = ref<Exchange[]>([]);
const allExchangesSelected = ref<boolean>(false);

const selectedQueries = ref<OnlineHistoryEventsQueryType[]>([]);
const allQueriesSelected = ref<boolean>(false);

const selectedProtocolQueries = ref<OnlineHistoryEventsQueryType[]>([]);
const allProtocolQueriesSelected = ref<boolean>(false);

const chains = useTemplateRef<ComponentExposed<typeof HistoryRefreshChains>>('chains');
const exchanges = useTemplateRef<ComponentExposed<typeof HistoryRefreshExchanges>>('exchanges');
const validatorEvents = useTemplateRef<ComponentExposed<typeof HistoryRefreshStakingEvents>>('validatorEvents');
const protocols = useTemplateRef<ComponentExposed<typeof HistoryRefreshProtocolEvents>>('protocols');

const { t } = useI18n({ useScope: 'global' });

const indeterminate = computed<boolean>(() => {
  switch (get(tab)) {
    case 'chains':
      return get(selectedAccounts).length > 0 && !get(allAccountsSelected);
    case 'exchanges':
      return get(selectedExchanges).length > 0 && !get(allExchangesSelected);
    case 'events':
      return get(selectedQueries).length > 0 && !get(allQueriesSelected);
    case 'protocols':
      return get(selectedProtocolQueries).length > 0 && !get(allProtocolQueriesSelected);
    default:
      return false;
  }
});

const selected = computed<boolean>(() => {
  switch (get(tab)) {
    case 'chains':
      return get(selectedAccounts).length > 0 && get(allAccountsSelected);
    case 'exchanges':
      return get(selectedExchanges).length > 0 && get(allExchangesSelected);
    case 'events':
      return get(selectedQueries).length > 0 && get(allQueriesSelected);
    case 'protocols':
      return get(selectedProtocolQueries).length > 0 && get(allProtocolQueriesSelected);
    default:
      return false;
  }
});

const totalSelected = computed<number>(() => {
  switch (get(tab)) {
    case 'chains':
      return get(selectedAccounts).length;
    case 'exchanges':
      return get(selectedExchanges).length;
    case 'events':
      return get(selectedQueries).length;
    case 'protocols':
      return get(selectedProtocolQueries).length;
    default:
      return 0;
  }
});

const searchLabel = computed<string>(() => {
  switch (get(tab)) {
    case 'chains':
      return isDefined(selectedChain)
        ? t('history_refresh_selection.search_address')
        : t('history_refresh_selection.search_chain');
    case 'exchanges':
      return t('history_refresh_selection.search_exchanges');
    case 'events':
      return t('history_refresh_selection.search_events');
    case 'protocols':
      return t('history_refresh_selection.search_protocols');
    default:
      return '';
  }
});

const typeText = computed<string>(() => {
  const total = get(totalSelected);
  switch (get(tab)) {
    case 'chains':
      return t('history_refresh_selection.type.accounts', total);
    case 'exchanges':
      return t('history_refresh_selection.type.exchanges', total);
    case 'events':
      return t('history_refresh_selection.type.events', total);
    case 'protocols':
      return t('history_refresh_selection.type.protocols', total);
    default:
      return '';
  }
});

function reset() {
  set(search, '');
  set(selectedChain, undefined);
  set(selectedAccounts, []);
  set(allAccountsSelected, false);
  set(selectedExchanges, []);
  set(allExchangesSelected, false);
  set(selectedQueries, []);
  set(allQueriesSelected, false);
  set(selectedProtocolQueries, []);
  set(allProtocolQueriesSelected, false);
}

function refresh() {
  switch (get(tab)) {
    case 'chains':
      emit('refresh', { accounts: get(selectedAccounts) });
      break;
    case 'exchanges':
      emit('refresh', { exchanges: get(selectedExchanges) });
      break;
    case 'events':
      emit('refresh', { queries: get(selectedQueries) });
      break;
    case 'protocols':
      emit('refresh', { queries: get(selectedProtocolQueries) });
      break;
    default:
      return '';
  }

  reset();
  set(open, false);
}

function toggleSelectAll() {
  switch (get(tab)) {
    case 'chains':
      get(chains)?.toggleSelectAll();
      break;
    case 'exchanges':
      get(exchanges)?.toggleSelectAll();
      break;
    case 'events':
      get(validatorEvents)?.toggleSelectAll();
      break;
    case 'protocols':
      get(protocols)?.toggleSelectAll();
      break;
  }
}

watch(tab, () => {
  reset();
});

onMounted(() => {
  reset();
});
</script>

<template>
  <RuiMenu
    v-model="open"
    class="!border-0"
    :popper="{ placement: 'bottom', offsetSkid: 35 }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        color="primary"
        class="px-3 py-3 rounded-l-none h-9 !outline-none"
        :disabled="disabled"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-chevrons-up-down"
          class="size-4"
        />
      </RuiButton>
    </template>

    <div class="w-[450px]">
      <div class="p-4 border-b border-default">
        <RuiTextField
          v-model="search"
          dense
          color="primary"
          variant="outlined"
          :label="searchLabel"
          prepend-icon="lu-search"
          hide-details
          clearable
        />
      </div>
      <RuiTabs v-model="tab">
        <RuiTab value="chains">
          {{ t('history_refresh_selection.tabs.chains') }}
        </RuiTab>
        <RuiTab value="exchanges">
          {{ t('history_refresh_selection.tabs.exchanges') }}
        </RuiTab>
        <RuiTab value="events">
          {{ t('history_refresh_selection.tabs.events') }}
        </RuiTab>
        <RuiTab value="protocols">
          {{ t('history_refresh_selection.tabs.protocols') }}
        </RuiTab>
      </RuiTabs>

      <div class="px-4 py-2 text-xs font-medium uppercase border-y border-default bg-rui-grey-50 dark:bg-rui-grey-900">
        {{ t('history_refresh_selection.selection') }}
      </div>

      <RuiTabItems v-model="tab">
        <RuiTabItem value="chains">
          <HistoryRefreshChains
            ref="chains"
            v-model:search="search"
            v-model:chain="selectedChain"
            v-model="selectedAccounts"
            :processing="processing"
            @update:all-selected="allAccountsSelected = $event"
          />
        </RuiTabItem>
        <RuiTabItem value="exchanges">
          <HistoryRefreshExchanges
            ref="exchanges"
            v-model:search="search"
            v-model="selectedExchanges"
            :processing="processing"
            @update:all-selected="allExchangesSelected = $event"
          />
        </RuiTabItem>
        <RuiTabItem value="events">
          <HistoryRefreshStakingEvents
            ref="validatorEvents"
            v-model="selectedQueries"
            v-model:search="search"
            :processing="processing"
            @update:all-selected="allQueriesSelected = $event"
          />
        </RuiTabItem>
        <RuiTabItem value="protocols">
          <HistoryRefreshProtocolEvents
            ref="protocols"
            v-model="selectedProtocolQueries"
            v-model:search="search"
            :processing="processing"
            @update:all-selected="allProtocolQueriesSelected = $event"
          />
        </RuiTabItem>
      </RuiTabItems>

      <div class="px-4 py-2 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
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
            variant="text"
            @click="reset()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="!(indeterminate || selected)"
            :loading="processing"
            @click="refresh()"
          >
            {{ t('history_refresh_selection.refresh', { total: totalSelected, type: typeText }) }}
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
