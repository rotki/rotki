<script lang="ts" setup>
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

const toggles = defineModel<{
  customizedEventsOnly: boolean;
  showIgnoredAssets: boolean;
  matchExactEvents: boolean;
}>('toggles', { required: true });

const sort = defineModel<{ column: string; ascending: boolean }>('sort', { required: true });

withDefaults(defineProps<{
  matchers: SearchMatcher<any, any>[];
  exportParams: HistoryEventRequestPayload;
  hideAccountSelector?: boolean;
  processing?: boolean;
}>(), {
  hideAccountSelector: false,
  processing: false,
});

const emit = defineEmits<{
  redecode: [payload: 'all' | 'page' | string[]];
}>();

const { t } = useI18n({ useScope: 'global' });

const customizedEventsOnly = useRefPropVModel(toggles, 'customizedEventsOnly');
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');

const { txChains } = useSupportedChains();
const txChainIds = useArrayMap(txChains, x => x.id);

const sortOptions = [
  { key: 'timestamp', label: t('transactions.sort.by_date') },
  { key: 'identifier', label: t('transactions.sort.by_recently_added') },
];

const selectedSort = computed({
  get() {
    return sort.value.column;
  },
  set(value: string) {
    sort.value = { column: value, ascending: value === 'timestamp' ? false : false };
  },
});
</script>

<template>
  <HistoryTableActions hide-divider>
    <template #filter>
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

    <RuiMenuSelect
      v-model="selectedSort"
      :options="sortOptions"
      :label="t('transactions.sort.label')"
      key-attr="key"
      text-attr="label"
      variant="outlined"
      dense
      class="w-[12rem]"
    />

    <HistoryRedecodeButton
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
  </HistoryTableActions>
</template>
