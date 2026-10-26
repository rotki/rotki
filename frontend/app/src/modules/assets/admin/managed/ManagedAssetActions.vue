<script setup lang="ts">
import type { Filters } from '@/modules/assets/admin/managed/asset-filter-keys';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { PillParams } from '@/modules/core/table/param-refs';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useManagedAssetActions } from '@/modules/assets/admin/managed/use-managed-asset-actions';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';

/**
 * The bar's param bag, owned by the page: it is one face of the same refs the request and the url
 * read, so bridging it here would be a second adapter onto them.
 */
const pillParams = defineModel<PillParams>('pillParams', { required: true });
const selected = defineModel<string[]>('selected', { required: true });
const selectionMode = defineModel<boolean>('selectionMode', { required: true });
const filtersModel = defineModel<Filters>('matches', { required: true });

const { ignoredHandling, spamDisabled = false } = defineProps<{
  fields: FieldDef[];
  /** Read-only here: which ignore actions apply, and when the ignored list needs re-fetching. */
  ignoredHandling: IgnoredAssetsHandlingType;
  spamDisabled?: boolean;
}>();

const emit = defineEmits<{
  'ignore': [ignored: boolean];
  'mark-spam': [];
  'refresh:ignored': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const pillLabels = usePillBarLabels();

const { clearSelection, disabledIgnoreActions, exitSelection } = useManagedAssetActions({
  ignoredHandling: () => ignoredHandling,
  onIgnoredStale: (): void => emit('refresh:ignored'),
  selected,
  selectionMode,
});
</script>

<template>
  <TableSelectionBar
    v-if="selectionMode"
    class="grow"
    :count="selected.length"
    exitable
    @clear="clearSelection()"
    @exit="exitSelection()"
  >
    <TableSelectionAction
      icon="lu-eye-off"
      :disabled="disabledIgnoreActions.ignore"
      :title="t('ignore_buttons.ignore_tooltip')"
      data-testid="managed-assets-ignore"
      @click="emit('ignore', true)"
    >
      {{ t('ignore_buttons.ignore') }}
    </TableSelectionAction>
    <TableSelectionAction
      icon="lu-eye"
      :disabled="disabledIgnoreActions.unIgnore"
      :title="t('ignore_buttons.unignore_tooltip')"
      data-testid="managed-assets-unignore"
      @click="emit('ignore', false)"
    >
      {{ t('ignore_buttons.unignore') }}
    </TableSelectionAction>
    <TableSelectionAction
      icon="lu-trash-2"
      color="error"
      :disabled="spamDisabled"
      :title="t('asset_table.mark_spam_tooltip')"
      data-testid="managed-assets-mark-spam"
      @click="emit('mark-spam')"
    >
      {{ t('asset_table.mark_spam') }}
    </TableSelectionAction>
  </TableSelectionBar>
  <template v-else>
    <RuiTooltip
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          data-testid="managed-assets-select"
          @click="selectionMode = true"
        >
          <template #prepend>
            <RuiIcon
              name="lu-copy-check"
              size="18"
            />
          </template>
          {{ t('common.actions.select') }}
        </RuiButton>
      </template>
      {{ t('asset_table.enter_selection_mode') }}
    </RuiTooltip>
    <PillFilterBar
      v-model:matches="filtersModel"
      v-model:params="pillParams"
      class="grow"
      :fields="fields"
      :labels="pillLabels"
    />
  </template>
</template>
