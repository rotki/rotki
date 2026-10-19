<script setup lang="ts">
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';

const selected = defineModel<string[]>('selected', { required: true });
const ignoredAssetsHandling = defineModel<IgnoredAssetsHandlingType>('ignoredAssetsHandling', { required: true });
const selectionMode = defineModel<boolean>('selectionMode', { required: true });

const emit = defineEmits<{
  'mass-ignore': [ignored: boolean];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Ignoring what is already ignored, or the reverse, has nothing to act on under that filter. */
const disabledIgnoreActions = computed<{ ignore: boolean; unIgnore: boolean }>(() => {
  const handling = get(ignoredAssetsHandling);
  return {
    ignore: get(selected).length === 0 || handling === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: get(selected).length === 0 || handling === IgnoredAssetHandlingType.EXCLUDE,
  };
});

function exitSelection(): void {
  set(selected, []);
  set(selectionMode, false);
}
</script>

<template>
  <TableSelectionBar
    v-if="selectionMode"
    class="grow"
    :count="selected.length"
    exitable
    @clear="selected = []"
    @exit="exitSelection()"
  >
    <TableSelectionAction
      icon="lu-eye-off"
      :disabled="disabledIgnoreActions.ignore"
      :title="t('ignore_buttons.ignore_tooltip')"
      data-testid="nft-balances-ignore"
      @click="emit('mass-ignore', true)"
    >
      {{ t('ignore_buttons.ignore') }}
    </TableSelectionAction>
    <TableSelectionAction
      icon="lu-eye"
      :disabled="disabledIgnoreActions.unIgnore"
      :title="t('ignore_buttons.unignore_tooltip')"
      data-testid="nft-balances-unignore"
      @click="emit('mass-ignore', false)"
    >
      {{ t('ignore_buttons.unignore') }}
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
          data-testid="nft-balances-select"
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
      {{ t('non_fungible_balances.enter_selection_mode') }}
    </RuiTooltip>
    <RuiButtonGroup
      v-model="ignoredAssetsHandling"
      variant="segmented"
      required
      size="sm"
      class="ml-auto"
      :aria-label="t('asset_table.filter_by_ignored_status')"
      data-testid="asset-filter-ignored"
    >
      <RuiButton :model-value="IgnoredAssetHandlingType.NONE">
        {{ t('non_fungible_balances.ignored_filter.all') }}
      </RuiButton>
      <RuiButton :model-value="IgnoredAssetHandlingType.EXCLUDE">
        {{ t('non_fungible_balances.ignored_filter.not_ignored') }}
      </RuiButton>
      <RuiButton :model-value="IgnoredAssetHandlingType.SHOW_ONLY">
        {{ t('non_fungible_balances.ignored_filter.ignored') }}
      </RuiButton>
    </RuiButtonGroup>
  </template>
</template>
