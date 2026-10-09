<script setup lang="ts">
import type { SavedViewState } from '@/modules/core/table/pill/composables/use-saved-views';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/staking/eth/use-eth-validator-filter';
import { SavedFilterLocations } from '@/modules/core/table/filtering';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';

const filters = defineModel<Filters>('filters', { required: true });
const selected = defineModel<number[]>('selected', { required: true });

const { deleting = false, fields } = defineProps<{
  fields: FieldDef[];
  deleting?: boolean;
}>();

const emit = defineEmits<{
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const pillLabels = usePillBarLabels();

/**
 * The saved-view state for this table's bar.
 *
 * @remarks
 * Every pill here is filter-bound, so a saved view is its `matches` alone. `params` stays in the
 * shape the store expects, since that shape is shared with the param-bound bars.
 */
const pillState = computed<SavedViewState>(() => ({
  matches: get(filters),
  params: {},
}));

function applyView(view: SavedView): void {
  set(filters, view.matches);
}
</script>

<template>
  <TableSelectionBar
    v-if="selected.length > 0"
    :count="selected.length"
    @clear="selected = []"
  >
    <RuiButton
      size="sm"
      variant="outlined"
      color="error"
      :loading="deleting"
      data-testid="validators-delete-selected"
      @click="emit('delete')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-trash-2"
          size="16"
        />
      </template>
      {{ t('common.actions.delete') }}
    </RuiButton>
  </TableSelectionBar>
  <PillFilterBar
    v-model:matches="filters"
    class="flex-1 min-w-64"
    :fields="fields"
    :labels="pillLabels"
  >
    <template #views="{ disabled }">
      <PillViewsMenu
        :fields="fields"
        :location="SavedFilterLocations.ETH_VALIDATORS"
        :state="pillState"
        :disabled="disabled"
        @apply="applyView($event)"
      />
    </template>
  </PillFilterBar>
</template>
