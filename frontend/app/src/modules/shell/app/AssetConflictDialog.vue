<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { AssetUpdateConflictResult, ConflictResolution } from '@/modules/assets/types';
import AssetConflictRow from '@/modules/shell/app/AssetConflictRow.vue';
import {
  getConflictFields,
  isDiff,
  useAssetConflictResolution,
} from '@/modules/shell/app/use-asset-conflict-resolution';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const { conflicts } = defineProps<{
  conflicts: AssetUpdateConflictResult[];
}>();

const emit = defineEmits<{
  cancel: [];
  resolve: [resolution: ConflictResolution];
}>();

const { t } = useI18n({ useScope: 'global' });

const tableHeaders = computed<DataTableColumn<AssetUpdateConflictResult>[]>(() => [
  {
    class: 'py-4',
    key: 'local',
    label: t('conflict_dialog.table.headers.local'),
  },
  {
    class: 'py-4',
    key: 'remote',
    label: t('conflict_dialog.table.headers.remote'),
  },
  {
    align: 'center',
    class: 'py-4',
    key: 'keep',
    label: t('conflict_dialog.table.headers.keep'),
  },
]);

const {
  activeStrategyForAll,
  duplicateIdentifiers,
  enableManualResolution,
  hasResolution,
  manualResolution,
  modelResolution,
  onStrategyChange,
  remaining,
  setResolution,
  valid,
  warnDuplicate,
} = useAssetConflictResolution(() => conflicts);

function resolve(): void {
  emit('resolve', get(modelResolution));
}

/** Dismissing the bulk choices keeps what the user already has, rather than abandoning the update. */
function cancel(): void {
  if (get(manualResolution)) {
    emit('cancel');
    return;
  }

  setResolution('local');
  resolve();
}

onMounted(() => {
  setResolution('remote');
});
</script>

<template>
  <BigDialog
    :title="t('conflict_dialog.title')"
    :action="{
      disabled: !valid,
      primary: !manualResolution ? t('conflict_dialog.keep_remote') : undefined,
      secondary: !manualResolution ? t('conflict_dialog.keep_local') : undefined,
    }"
    :layout="{ autoHeight: !manualResolution, divide: true, maxWidth: '75rem' }"
    :persistent="hasResolution"
    display
    @confirm="resolve()"
    @cancel="cancel()"
  >
    <template #subtitle>
      <i18n-t
        scope="global"
        keypath="conflict_dialog.subtitle"
        tag="span"
      >
        <template #conflicts>
          <span class="font-medium"> {{ conflicts.length }} </span>
        </template>
        <template #remaining>
          <span class="font-medium"> {{ remaining }} </span>
        </template>
      </i18n-t>
    </template>
    <template #default>
      <RuiAlert
        v-if="warnDuplicate"
        class="my-2"
        type="warning"
      >
        <i18n-t
          scope="global"
          keypath="conflict_dialog.duplicate_warn"
          tag="span"
        >
          <template #identifiers>
            <strong> {{ duplicateIdentifiers.join(', ') }} </strong>
          </template>
        </i18n-t>
      </RuiAlert>
      <div
        v-if="!manualResolution"
        class="text-subtitle-1 flex flex-col"
      >
        <p class="mb-2">
          {{ t('conflict_dialog.action_hint.top') }}
        </p>
        <ul class="pl-0 mb-6">
          <li>
            <span class="font-medium">- {{ t('conflict_dialog.keep_local') }}:</span>
            {{ t('conflict_dialog.keep_local_tooltip') }}
          </li>
          <li>
            <span class="font-medium">- {{ t('conflict_dialog.keep_remote') }}:</span>
            {{ t('conflict_dialog.keep_remote_tooltip') }}
          </li>
        </ul>
        <p class="mb-0">
          {{ t('conflict_dialog.action_hint.bottom') }}
        </p>
      </div>
      <template v-else>
        <div class="flex mt-4 mb-6">
          <RuiTooltip
            :options="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                :active="activeStrategyForAll.local"
                :variant="activeStrategyForAll.local ? 'default' : 'outlined'"
                value="local"
                color="primary"
                class="!rounded-r-none"
                @click="setResolution('local')"
              >
                {{ t('conflict_dialog.keep_local') }}
              </RuiButton>
            </template>
            {{ t('conflict_dialog.keep_local_tooltip') }}
          </RuiTooltip>
          <RuiTooltip
            :options="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                :active="activeStrategyForAll.remote"
                :variant="activeStrategyForAll.remote ? 'default' : 'outlined'"
                color="primary"
                value="remote"
                class="!rounded-l-none"
                @click="setResolution('remote')"
              >
                {{ t('conflict_dialog.keep_remote') }}
              </RuiButton>
            </template>
            {{ t('conflict_dialog.keep_remote_tooltip') }}
          </RuiTooltip>
        </div>

        <RuiDataTable
          :rows="conflicts"
          :cols="tableHeaders"
          row-attr="identifier"
          outlined
          dense
        >
          <template #item.local="{ row: conflict }">
            <AssetConflictRow
              v-for="field in getConflictFields(conflict)"
              :key="`local-${field}`"
              :field="field"
              :value="conflict.local[field]"
              :diff="isDiff(conflict, field)"
            />
          </template>
          <template #item.remote="{ row: conflict }">
            <AssetConflictRow
              v-for="field in getConflictFields(conflict)"
              :key="`remote-${field}`"
              :field="field"
              :value="conflict.remote[field]"
              :diff="isDiff(conflict, field)"
            />
          </template>
          <template #item.keep="{ row: conflict }">
            <RuiButtonGroup
              v-model="modelResolution[conflict.identifier]"
              color="primary"
              variant="outlined"
              @update:model-value="onStrategyChange(modelResolution[conflict.identifier])"
            >
              <RuiButton model-value="local">
                {{ t('conflict_dialog.action.local') }}
              </RuiButton>
              <RuiButton model-value="remote">
                {{ t('conflict_dialog.action.remote') }}
              </RuiButton>
            </RuiButtonGroup>
          </template>
        </RuiDataTable>
      </template>
    </template>
    <template
      v-if="!manualResolution"
      #left-buttons
    >
      <RuiButton
        data-testid="manage-conflicts"
        color="primary"
        variant="text"
        @click="enableManualResolution()"
      >
        {{ t('conflict_dialog.manage') }}
      </RuiButton>
    </template>
  </BigDialog>
</template>
