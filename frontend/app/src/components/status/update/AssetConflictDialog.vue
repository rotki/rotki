<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common/lib/data';
import type { DataTableColumn } from '@rotki/ui-library-compat';
import type { Writeable } from '@/types';
import type {
  AssetUpdateConflictResult,
  ConflictResolution,
} from '@/types/asset';
import type { ConflictResolutionStrategy } from '@/types/common';

const props = defineProps<{
  conflicts: AssetUpdateConflictResult[];
}>();

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'resolve', resolution: ConflictResolution): void;
}>();

const { t } = useI18n();

const { conflicts } = toRefs(props);

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('conflict_dialog.table.headers.local'),
    key: 'local',
    class: 'py-4',
  },
  {
    label: t('conflict_dialog.table.headers.remote'),
    key: 'remote',
    class: 'py-4',
  },
  {
    label: t('conflict_dialog.table.headers.keep'),
    key: 'keep',
    align: 'center',
    class: 'py-4',
  },
]);

const resolution: Ref<ConflictResolution> = ref({});
const strategyModeForAll = ref<ConflictResolutionStrategy>();
const resolutionLength = computed(() => Object.keys(get(resolution)).length);
const isAllLocalOrRemote = computed(() => {
  if (get(conflicts).length === 0 || get(resolutionLength) !== get(conflicts).length)
    return undefined;

  return get(strategyModeForAll);
});

function setResolution(strategy: ConflictResolutionStrategy) {
  const length = get(conflicts).length;
  const resolutionStrategy: Writeable<ConflictResolution> = {};
  for (let i = 0; i < length; i++) {
    const conflict = get(conflicts)[i];
    resolutionStrategy[conflict.identifier] = strategy;
  }

  set(resolution, resolutionStrategy);
  set(strategyModeForAll, strategy);
}

function onStrategyChange(strategy?: ConflictResolutionStrategy) {
  if (Object.values(get(resolution)).every(strat => strat === strategy))
    set(strategyModeForAll, strategy);
  else
    set(strategyModeForAll, undefined);
}

type AssetKey = keyof SupportedAsset;

function getConflictFields(conflict: AssetUpdateConflictResult): AssetKey[] {
  function nonNull(key: AssetKey, asset: SupportedAsset): boolean {
    return asset[key] !== null;
  }
  const remote = Object.keys(conflict.remote).filter(value =>
    nonNull(value as AssetKey, conflict.remote),
  );
  const local = Object.keys(conflict.local).filter(value =>
    nonNull(value as AssetKey, conflict.local),
  );
  return [...remote, ...local].filter(uniqueStrings) as AssetKey[];
}

function isDiff(conflict: AssetUpdateConflictResult, field: AssetKey) {
  const localElement = conflict.local[field];
  const remoteElement = conflict.remote[field];
  return localElement !== remoteElement;
}

const remaining = computed(() => {
  const resolved = get(resolutionLength);
  return get(conflicts).length - resolved;
});

const valid = computed(() => {
  const identifiers = get(conflicts)
    .map(({ identifier }) => identifier)
    .sort();
  const resolved = Object.keys(get(resolution)).sort();
  if (identifiers.length !== resolved.length)
    return false;

  for (const [i, element] of resolved.entries()) {
    if (element !== identifiers[i])
      return false;
  }
  return true;
});

function resolve(resolution: ConflictResolution) {
  emit('resolve', resolution);
}

function cancel() {
  emit('cancel');
}

onMounted(() => {
  setResolution('remote');
});
</script>

<template>
  <BigDialog
    :display="true"
    :title="t('conflict_dialog.title')"
    :subtitle="t('conflict_dialog.subtitle')"
    :action-disabled="!valid"
    max-width="1200px"
    :persistent="resolutionLength > 0"
    @confirm="resolve(resolution)"
    @cancel="cancel()"
  >
    <template #default="{ wrapper }">
      <div
        class="flex justify-between items-center gap-8 border border-default rounded p-4"
      >
        <span class="text-body-1">
          {{ t('conflict_dialog.all_buttons_description') }}
        </span>
        <RuiButtonGroup
          color="primary"
          variant="outlined"
          :value="isAllLocalOrRemote"
        >
          <template #default>
            <RuiButton
              value="local"
              @click="setResolution('local')"
            >
              {{ t('conflict_dialog.keep_local') }}
            </RuiButton>
            <RuiButton
              value="remote"
              @click="setResolution('remote')"
            >
              {{ t('conflict_dialog.keep_remote') }}
            </RuiButton>
          </template>
        </RuiButtonGroup>
      </div>

      <div class="text-subtitle-1 my-6">
        <i18n
          path="conflict_dialog.hint"
          tag="span"
        >
          <template #conflicts>
            <span class="font-medium"> {{ conflicts.length }} </span>
          </template>
          <template #remaining>
            <span class="font-medium"> {{ remaining }} </span>
          </template>
        </i18n>
      </div>

      <RuiDataTable
        :rows="conflicts"
        :cols="tableHeaders"
        :scroller="wrapper"
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
            v-model="resolution[conflict.identifier]"
            color="primary"
            variant="outlined"
            @input="onStrategyChange(resolution[conflict.identifier])"
          >
            <template #default>
              <RuiButton value="local">
                {{ t('conflict_dialog.action.local') }}
              </RuiButton>
              <RuiButton value="remote">
                {{ t('conflict_dialog.action.remote') }}
              </RuiButton>
            </template>
          </RuiButtonGroup>
        </template>
      </RuiDataTable>
    </template>
  </BigDialog>
</template>

<style module lang="scss">
.mobile {
  :global {
    .v-data-table {
      &__mobile-row {
        padding: 12px 16px !important;

        &__header {
          text-orientation: sideways;
          writing-mode: vertical-lr;
        }
      }

      &__mobile-table-row {
        td {
          &:nth-child(2) {
            background-color: rgba(0, 0, 0, 0.1);
          }
        }
      }
    }
  }
}
</style>
