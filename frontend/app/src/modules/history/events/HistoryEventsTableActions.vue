<script lang="ts" setup>
import type { SavedViewState } from '@/modules/core/table/pill/composables/use-saved-views';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import type { FieldDef, PillBarLabels } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { IgnoreStatus } from '@/modules/history/events/use-history-events-selection-actions';
import type { SelectionState } from '@/modules/history/events/use-selection-mode';
import { arrayify } from '@/modules/core/common/data/array';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { type MatchedKeywordWithBehaviour, SavedFilterLocation } from '@/modules/core/table/filtering';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';
import HistoryEventsExport from '@/modules/history/events/HistoryEventsExport.vue';
import { isValidHistoryEventState } from '@/modules/history/events/mapping/use-history-event-state-mapping';
import HistoryTableActions from '@/modules/history/HistoryTableActions.vue';
import HistoryRedecodeButton from '@/modules/history/redecode/HistoryRedecodeButton.vue';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const locationLabels = defineModel<string[]>('locationLabels', { required: true });

const action = defineModel<string | undefined>('action', { required: true });

const toggles = defineModel<HistoryEventsToggles>('toggles', { required: true });

const { ignoreStatus } = defineProps<{
  fields: FieldDef[];
  exportParams: HistoryEventRequestPayload;
  hideRedecodeButtons?: boolean;
  ignoreStatus?: IgnoreStatus;
  processing?: boolean;
  selection: SelectionState;
}>();

const emit = defineEmits<{
  'redecode': [payload: 'all' | 'page' | string[]];
  'selection:action': [action: 'toggle-mode' | 'delete' | 'exit' | 'toggle-all' | 'create-rule' | 'ignore' | 'unignore' | 'toggle-select-all-matching'];
}>();

const { t } = useI18n({ useScope: 'global' });

// Not a pill: it constrains how the other filters apply instead of filtering anything itself.
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');

const pillLabels = computed<PillBarLabels>(() => ({
  add: t('transactions.filter.pill_add'),
  clear: t('transactions.filter.pill_clear'),
  empty: t('transactions.filter.pill_empty'),
  narrow: t('transactions.filter.pill_narrow'),
  narrowEmpty: t('transactions.filter.pill_narrow_empty'),
  remove: t('transactions.filter.pill_remove'),
  search: t('transactions.filter.pill_search'),
}));

// The account, state and show-ignored filters are param-bound pills in the bar (paramKeys
// `locationLabels`, `stateMarkers`, `showIgnoredAssets`). Bridge the bar's param bag to the models
// that back them so the bar drives the same sources the standalone selector and dropdown used to.
// An absent param clears its model — for the boolean that is the pill's whole state, since
// removing it is how it is turned off.
const pillParams = computed<Record<string, string | string[] | boolean>>({
  get(): Record<string, string | string[] | boolean> {
    const labels = get(locationLabels);
    const { showIgnoredAssets, stateMarkers } = get(toggles);
    const result: Record<string, string | string[] | boolean> = {};
    const verb = get(action);
    if (verb !== undefined)
      result.action = verb;
    if (labels.length > 0)
      result.locationLabels = labels;
    if (stateMarkers.length > 0)
      result.stateMarkers = stateMarkers;
    if (showIgnoredAssets)
      result.showIgnoredAssets = true;
    return result;
  },
  set(value: Record<string, string | string[] | boolean>): void {
    const nextAction = value.action;
    set(action, typeof nextAction === 'string' ? nextAction : undefined);

    const nextLabels = value.locationLabels;
    set(locationLabels, nextLabels === undefined || typeof nextLabels === 'boolean' ? [] : arrayify(nextLabels));

    const nextMarkers = value.stateMarkers;
    set(toggles, {
      ...get(toggles),
      showIgnoredAssets: value.showIgnoredAssets === true,
      stateMarkers: nextMarkers === undefined || typeof nextMarkers === 'boolean'
        ? []
        : arrayify(nextMarkers).filter(isValidHistoryEventState),
    });
  },
});

// A saved view is the bar's two models under a name, so it both reads from and writes to the same
// pair the bar is bound to.
const pillState = computed<SavedViewState>(() => ({
  matches: get(filters),
  params: get(pillParams),
}));

function applyView(view: SavedView): void {
  set(filters, view.matches);
  set(pillParams, view.params);
}

const canIgnore = computed<boolean>(() => {
  const status = ignoreStatus;
  return status ? status.notIgnoredCount > 0 : false;
});

const canUnignore = computed<boolean>(() => {
  const status = ignoreStatus;
  return status ? status.ignoredCount > 0 : false;
});

function handleDelete(): void {
  emit('selection:action', 'delete');
}

function handleCreateRule(): void {
  emit('selection:action', 'create-rule');
}

function handleIgnore(): void {
  emit('selection:action', 'ignore');
}

function handleUnignore(): void {
  emit('selection:action', 'unignore');
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

function handleToggleSelectAllMatching(): void {
  emit('selection:action', 'toggle-select-all-matching');
}
</script>

<template>
  <HistoryTableActions hide-divider>
    <template #filter>
      <PillFilterBar
        v-model:matches="filters"
        v-model:params="pillParams"
        class="flex-1 min-w-[12rem] md:min-w-[24rem]"
        :fields="fields"
        :labels="pillLabels"
      >
        <template #views="{ disabled: barDisabled }">
          <PillViewsMenu
            :fields="fields"
            :location="SavedFilterLocation.HISTORY_EVENTS"
            :state="pillState"
            :disabled="barDisabled"
            @apply="applyView($event)"
          />
        </template>

        <!-- Constrains the active filters to the events themselves rather than their whole
             group, so it only means anything once something is filtered.

             An icon toggle rather than a labelled switch: it sits inside the bar, where the
             pills are what should be read, and its label is long enough to crowd them out. The
             tooltip carries the full name and the explanation the switch's hint used to. -->
        <template #modifiers="{ disabled: barDisabled }">
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                size="sm"
                icon
                class="shrink-0"
                :disabled="barDisabled"
                :color="matchExactEvents ? 'primary' : 'secondary'"
                :class="{ 'bg-rui-primary/10': matchExactEvents }"
                :aria-pressed="matchExactEvents"
                data-testid="filter-match-exact"
                @click="matchExactEvents = !matchExactEvents"
              >
                <RuiIcon
                  name="lu-focus"
                  size="18"
                />
              </RuiButton>
            </template>
            <div class="max-w-[16rem]">
              <div class="font-medium">
                {{ t('transactions.filter.match_exact_filter') }}
              </div>
              <!-- An icon toggle has no label to read its state from, so the tooltip says which
                   state it is in rather than only what the setting means. -->
              <div class="text-caption">
                {{ matchExactEvents
                  ? t('transactions.filter.match_exact_filter_enabled')
                  : t('transactions.filter.match_exact_filter_disabled') }}
              </div>
            </div>
          </RuiTooltip>
        </template>
      </PillFilterBar>
    </template>

    <div
      v-if="selection.isActive"
      class="flex items-center gap-1.5 h-10 bg-rui-grey-500/[0.1] rounded-md pl-3 pr-1"
    >
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiCheckbox
            :model-value="selection.isAllSelected || selection.selectAllMatching"
            :indeterminate="selection.isPartiallySelected"
            :disabled="selection.selectAllMatching"
            color="primary"
            hide-details
            size="sm"
            @update:model-value="handleToggleAll()"
          />
        </template>
        {{ t('transactions.events.selection_mode.select_all_page') }}
      </RuiTooltip>
      <span
        v-if="!selection.selectAllMatching"
        class="text-sm text-rui-text-secondary -ml-1 mr-2 select-none"
      >
        {{ t('transactions.events.selection_mode.selected_count', { count: selection.selectedCount }) }}
      </span>
      <RuiDivider
        v-if="!selection.selectAllMatching"
        vertical
        class="mr-1 -ml-1 h-4"
      />
      <RuiButton
        variant="text"
        :color="selection.selectAllMatching ? 'warning' : 'primary'"
        size="sm"
        class="text-sm hover:underline cursor-pointer mr-2"
        :class="selection.selectAllMatching ? '-ml-3' : '-ml-1'"
        @click="handleToggleSelectAllMatching()"
      >
        {{ selection.selectAllMatching ? t('transactions.events.selection_mode.all_matching_selected', { count: selection.totalMatchingCount }) : t('transactions.events.selection_mode.select_all_matching') }}
        <template
          v-if="selection.selectAllMatching"
          #append
        >
          <RuiIcon
            name="lu-x"
            size="18"
          />
        </template>
      </RuiButton>
      <RuiTooltip :open-delay="200">
        <template #activator>
          <RuiButton
            color="error"
            variant="outlined"
            class="h-7 px-2.5"
            :disabled="selection.selectedCount === 0"
            @click="handleDelete()"
          >
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('transactions.events.selection_mode.delete_selected') }}
      </RuiTooltip>
      <div class="flex">
        <RuiTooltip :open-delay="200">
          <template #activator>
            <RuiButton
              variant="outlined"
              class="h-7 px-2.5 !rounded-r-none"
              :disabled="selection.selectedCount === 0 || !canIgnore || selection.selectAllMatching"
              @click="handleIgnore()"
            >
              <RuiIcon
                name="lu-eye-off"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('transactions.events.selection_mode.ignore') }}
        </RuiTooltip>
        <RuiTooltip :open-delay="200">
          <template #activator>
            <RuiButton
              variant="outlined"
              class="h-7 px-2.5 !rounded-l-none -ml-[1px]"
              :disabled="selection.selectedCount === 0 || !canUnignore || selection.selectAllMatching"
              @click="handleUnignore()"
            >
              <RuiIcon
                name="lu-eye"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('transactions.events.selection_mode.unignore') }}
        </RuiTooltip>
      </div>
      <RuiTooltip :open-delay="200">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            class="h-7 px-2.5"
            :disabled="selection.selectedCount === 0 || selection.selectAllMatching"
            @click="handleCreateRule()"
          >
            <RuiIcon
              name="lu-file-spreadsheet"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('transactions.events.selection_mode.create_rule') }}
      </RuiTooltip>
      <RuiButton
        variant="text"
        class="h-7 px-2.5"
        @click="handleExit()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
    </div>
    <template v-else>
      <RuiTooltip :open-delay="200">
        <template #activator>
          <RuiButton
            variant="text"
            size="xl"
            :disabled="!selection.hasAvailableEvents"
            @click="handleToggleMode()"
          >
            <template #prepend>
              <RuiIcon name="lu-copy-check" />
            </template>
          </RuiButton>
        </template>
        {{ selection.hasAvailableEvents ? t('transactions.events.selection_mode.tooltip') : t('transactions.events.selection_mode.no_events') }}
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
    </template>
  </HistoryTableActions>
</template>
