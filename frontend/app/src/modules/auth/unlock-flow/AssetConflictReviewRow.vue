<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import type { AssetUpdateConflictResult } from '@/modules/assets/types';
import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';
import { RuiButton, RuiButtonGroup } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import AssetConflictValue from '@/modules/shell/app/AssetConflictValue.vue';
import { getConflictFields, isDiff } from '@/modules/shell/app/use-asset-conflict-resolution';

const { conflict } = defineProps<{
  conflict: AssetUpdateConflictResult;
  /** The side chosen for this asset, whose column reads bolder. */
  strategy?: ConflictResolutionStrategy;
}>();

const emit = defineEmits<{
  choose: [strategy: ConflictResolutionStrategy];
}>();

const { t } = useI18n({ useScope: 'global' });

const name = computed<string>(() => {
  const { local, remote } = conflict;
  const assetName = remote.name ?? local.name;
  const symbol = remote.symbol ?? local.symbol;
  if (assetName && symbol)
    return `${assetName} (${symbol})`;
  return assetName ?? symbol ?? conflict.identifier;
});

/** The fields the two sides disagree on; all of them when nothing differs, so the row is never empty. */
const fields = computed<(keyof SupportedAsset)[]>(() => {
  const all = getConflictFields(conflict);
  const differing = all.filter(field => isDiff(conflict, field));
  return differing.length > 0 ? differing : all;
});
</script>

<template>
  <li
    class="p-4 flex flex-col gap-3"
    data-testid="asset-conflict"
  >
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-body-1 font-medium break-words">
          {{ name }}
        </div>
        <div class="text-caption text-rui-text-secondary break-all">
          {{ conflict.identifier }}
        </div>
      </div>
      <RuiButtonGroup
        :model-value="strategy"
        variant="segmented"
        size="sm"
        required
        @update:model-value="emit('choose', $event)"
      >
        <RuiButton model-value="local">
          {{ t('unlock_flow.asset_update.conflicts.review.keep_local') }}
        </RuiButton>
        <RuiButton model-value="remote">
          {{ t('unlock_flow.asset_update.conflicts.review.use_remote') }}
        </RuiButton>
      </RuiButtonGroup>
    </div>

    <table class="w-full text-body-2 table-fixed">
      <thead>
        <tr class="text-caption text-rui-text-secondary text-left">
          <th class="font-normal pb-1 pr-3 w-1/4">
            {{ t('unlock_flow.asset_update.conflicts.review.field') }}
          </th>
          <th class="font-normal pb-1 pr-3">
            {{ t('unlock_flow.asset_update.conflicts.review.local') }}
          </th>
          <th class="font-normal pb-1">
            {{ t('unlock_flow.asset_update.conflicts.review.remote') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="field in fields"
          :key="field"
          class="align-top"
        >
          <td class="py-1 pr-3 text-rui-text-secondary break-words">
            {{ field }}
          </td>
          <td
            class="py-1 pr-3"
            :class="{ 'font-medium': strategy === 'local' }"
          >
            <AssetConflictValue
              :field="field"
              :value="conflict.local[field]"
            />
          </td>
          <td
            class="py-1"
            :class="{ 'font-medium': strategy === 'remote' }"
          >
            <AssetConflictValue
              :field="field"
              :value="conflict.remote[field]"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </li>
</template>
