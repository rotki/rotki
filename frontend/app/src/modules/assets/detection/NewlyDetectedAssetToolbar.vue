<script setup lang="ts">
import type { Filters } from '@/modules/assets/detection/use-newly-detected-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

const filtersModel = defineModel<Filters>('filters', { required: true });

const {
  allSelected,
  selectedCount,
  found,
  fields,
} = defineProps<{
  allSelected: boolean;
  selectedCount: number;
  found: number;
  fields: FieldDef[];
}>();

const emit = defineEmits<{
  'toggle-selection': [];
  'clear-selection': [];
  'accept': [];
  'mark-spam': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();
</script>

<template>
  <TableSelectionBar
    v-if="selectedCount > 0"
    class="grow"
    :count="selectedCount"
    @clear="emit('clear-selection')"
  >
    <template #scope>
      <RuiButton
        v-if="!allSelected"
        variant="text"
        size="sm"
        color="primary"
        data-testid="select-all-matching"
        @click="emit('toggle-selection')"
      >
        {{ t('asset_table.newly_detected.select_all_matching', { count: found }) }}
      </RuiButton>
    </template>
    <TableSelectionAction
      icon="lu-check"
      color="success"
      data-testid="accept-selected"
      @click="emit('accept')"
    >
      {{ t('asset_table.newly_detected.accept_selected') }}
    </TableSelectionAction>
    <TableSelectionAction
      icon="lu-octagon-alert"
      color="error"
      data-testid="mark-selected-spam"
      @click="emit('mark-spam')"
    >
      {{ t('asset_table.newly_detected.mark_selected_as_spam') }}
    </TableSelectionAction>
  </TableSelectionBar>
  <template v-else>
    <HintMenuIcon>
      {{ t('asset_table.newly_detected.subtitle') }}
    </HintMenuIcon>
    <PillFilterBar
      v-if="fields.length > 0"
      v-model:matches="filtersModel"
      class="flex-1 min-w-48 md:min-w-96"
      :fields="fields"
      :labels="pillLabels"
    />
  </template>
</template>
