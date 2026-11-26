<script setup lang="ts">
import type { Filters } from '@/modules/history/internal-tx-conflicts/internal-tx-conflict-filter-keys';
import type { ResolutionProgress } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflict-resolution';
import { RuiButton, RuiProgress } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';
import { useInternalTxConflictFields } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflict-fields';

const filters = defineModel<Filters>('filters', { required: true });

const { compact = false, loading, progress, selectedCount } = defineProps<{
  compact?: boolean;
  loading: boolean;
  progress: ResolutionProgress;
  selectedCount: number;
}>();

const emit = defineEmits<{
  'cancel': [];
  'clear': [];
  'resolve-selected': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const fields = useInternalTxConflictFields();
const pillLabels = usePillBarLabels();
</script>

<template>
  <div
    class="flex flex-col gap-2 pt-4 pb-2 shrink-0"
    :class="compact ? 'px-3' : 'px-4 md:flex-row md:items-center'"
  >
    <div
      v-if="progress.isRunning"
      class="flex items-center gap-3"
    >
      <RuiProgress
        variant="indeterminate"
        color="primary"
        class="flex-1"
      />
      <span class="text-body-2 whitespace-nowrap">
        {{ t('internal_tx_conflicts.resolution.progress', { completed: progress.completed, total: progress.total }) }}
      </span>
      <RuiButton
        variant="outlined"
        color="error"
        size="sm"
        @click="emit('cancel')"
      >
        {{ t('internal_tx_conflicts.resolution.cancel') }}
      </RuiButton>
    </div>

    <TableSelectionBar
      v-if="!progress.isRunning && selectedCount > 0"
      class="flex-1"
      :count="selectedCount"
      @clear="emit('clear')"
    >
      <TableSelectionAction
        icon="lu-wrench"
        color="primary"
        data-testid="resolve-selected"
        @click="emit('resolve-selected')"
      >
        {{ t('internal_tx_conflicts.resolution.resolve_selected', { count: selectedCount }) }}
      </TableSelectionAction>
    </TableSelectionBar>
    <PillFilterBar
      v-else
      v-model:matches="filters"
      :fields="fields"
      :labels="pillLabels"
      :disabled="loading"
      class="flex-1"
    />
  </div>
</template>
