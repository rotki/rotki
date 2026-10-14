<script setup lang="ts">
import type { Filters } from '@/modules/assets/admin/managed/use-assets-filter';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { PillParams } from '@/modules/core/table/param-refs';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useManagedAssetActions } from '@/modules/assets/admin/managed/use-managed-asset-actions';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';

/**
 * The bar's param bag, owned by the page: it is one face of the same refs the request and the url
 * read, so bridging it here would be a second adapter onto them.
 */
const pillParams = defineModel<PillParams>('pillParams', { required: true });
const selected = defineModel<string[]>('selected', { required: true });
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

const { clearSelection, disabledIgnoreActions } = useManagedAssetActions({
  ignoredHandling: () => ignoredHandling,
  onIgnoredStale: (): void => emit('refresh:ignored'),
  selected,
});
</script>

<template>
  <TableSelectionBar
    v-if="selected.length > 0"
    class="grow"
    :count="selected.length"
    @clear="clearSelection()"
  >
    <RuiButton
      size="sm"
      variant="outlined"
      :disabled="disabledIgnoreActions.ignore"
      :title="t('ignore_buttons.ignore_tooltip')"
      data-testid="managed-assets-ignore"
      @click="emit('ignore', true)"
    >
      <template #prepend>
        <RuiIcon
          name="lu-eye-off"
          size="16"
        />
      </template>
      {{ t('ignore_buttons.ignore') }}
    </RuiButton>
    <RuiButton
      size="sm"
      variant="outlined"
      :disabled="disabledIgnoreActions.unIgnore"
      :title="t('ignore_buttons.unignore_tooltip')"
      data-testid="managed-assets-unignore"
      @click="emit('ignore', false)"
    >
      <template #prepend>
        <RuiIcon
          name="lu-eye"
          size="16"
        />
      </template>
      {{ t('ignore_buttons.unignore') }}
    </RuiButton>
    <RuiButton
      size="sm"
      variant="outlined"
      color="error"
      :disabled="spamDisabled"
      :title="t('asset_table.mark_spam_tooltip')"
      data-testid="managed-assets-mark-spam"
      @click="emit('mark-spam')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-trash-2"
          size="16"
        />
      </template>
      {{ t('asset_table.mark_spam') }}
    </RuiButton>
  </TableSelectionBar>
  <PillFilterBar
    v-else
    v-model:matches="filtersModel"
    v-model:params="pillParams"
    class="grow"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
