<script setup lang="ts">
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import { useHistoryEventStateMapping } from '@/composables/history/events/mapping/state';
import { HistoryEventState } from '@/types/history/events/schemas';
import { useRefPropVModel } from '@/utils/model';

const toggles = defineModel<HistoryEventsToggles>('toggles', { required: true });

const { t } = useI18n({ useScope: 'global' });
const { stateConfigs } = useHistoryEventStateMapping();

const stateMarkers = useRefPropVModel(toggles, 'stateMarkers');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');

const stateOptions = Object.values(HistoryEventState).map(state => ({
  value: state,
  ...stateConfigs[state],
}));

const hasActiveToggles = computed<boolean>(
  () => get(stateMarkers).length > 0 || get(showIgnoredAssets) || get(matchExactEvents),
);

function isChecked(state: HistoryEventState): boolean {
  return get(stateMarkers).includes(state);
}

function toggleState(state: HistoryEventState): void {
  const current = get(stateMarkers);
  if (current.includes(state))
    set(stateMarkers, current.filter(s => s !== state));
  else
    set(stateMarkers, [...current, state]);
}
</script>

<template>
  <RuiBadge
    dot
    :model-value="hasActiveToggles"
    offset-y="10"
    offset-x="-8"
  >
    <TableStatusFilter
      menu-class="w-[20rem]"
    >
      <div class="flex flex-col py-2 pb-3">
        <div class="px-4 py-2 text-body-1 text-rui-text-secondary font-medium">
          {{ t('transactions.filter.state_markers') }}
        </div>
        <div
          v-for="option in stateOptions"
          :key="option.value"
        >
          <RuiCheckbox
            :model-value="isChecked(option.value)"
            color="primary"
            class="px-4 -my-1 [&_span]:!text-sm [&_span]:!my-auto"
            hide-details
            @update:model-value="toggleState(option.value)"
          >
            <div class="flex items-center gap-1.5">
              <RuiIcon
                :name="option.icon"
                size="14"
                :color="option.color"
              />
              {{ option.label }}
            </div>
          </RuiCheckbox>
        </div>
      </div>
      <RuiDivider />
      <RuiSwitch
        v-model="showIgnoredAssets"
        color="primary"
        class="p-4"
        size="sm"
        hide-details
        :label="t('transactions.filter.show_ignored_assets')"
      />
      <RuiDivider />
      <RuiSwitch
        v-model="matchExactEvents"
        color="primary"
        class="p-4"
        size="sm"
        :label="t('transactions.filter.match_exact_filter')"
        :hint="t('transactions.filter.match_exact_filter_hint')"
      />
    </TableStatusFilter>
  </RuiBadge>
</template>
