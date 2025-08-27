<script lang="ts" setup>
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import HistoryEventsExport from '@/components/history/events/HistoryEventsExport.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import LocationLabelSelector from '@/components/history/LocationLabelSelector.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import HistoryRedecodeButton from '@/modules/history/redecode/HistoryRedecodeButton.vue';
import { type MatchedKeywordWithBehaviour, SavedFilterLocation, type SearchMatcher } from '@/types/filtering';
import { useRefPropVModel } from '@/utils/model';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const locationLabels = defineModel<string[]>('locationLabels', { required: true });

const toggles = defineModel<{
  customizedEventsOnly: boolean;
  showIgnoredAssets: boolean;
  matchExactEvents: boolean;
}>('toggles', { required: true });

withDefaults(defineProps<{
  matchers: SearchMatcher<any, any>[];
  exportParams: HistoryEventRequestPayload;
  hideAccountSelector?: boolean;
  hideRedecodeButtons?: boolean;
  processing?: boolean;
}>(), {
  hideAccountSelector: false,
  hideRedecodeButtons: false,
  processing: false,
});

const emit = defineEmits<{
  redecode: [payload: 'all' | 'page' | string[]];
}>();

const { t } = useI18n({ useScope: 'global' });

const customizedEventsOnly = useRefPropVModel(toggles, 'customizedEventsOnly');
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');
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

    <HistoryRedecodeButton
      v-if="!hideRedecodeButtons"
      :processing="processing"
      @redecode="emit('redecode', $event)"
    />

    <HistoryEventsExport
      :match-exact-events="toggles.matchExactEvents"
      :filters="exportParams"
    />

    <LocationLabelSelector
      v-if="!hideAccountSelector"
      v-model="locationLabels"
    />
  </HistoryTableActions>
</template>
