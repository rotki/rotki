<script setup lang="ts">
import { type SupportedAsset } from '@rotki/common/lib/data';
import { type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type Writeable } from '@/types';
import {
  type AssetUpdateConflictResult,
  type ConflictResolution
} from '@/types/asset';
import { type ConflictResolutionStrategy } from '@/types/common';

const props = defineProps<{
  conflicts: AssetUpdateConflictResult[];
}>();

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'resolve', resolution: ConflictResolution): void;
}>();

const { t } = useI18n();

const { conflicts } = toRefs(props);

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('conflict_dialog.table.headers.local'),
    sortable: false,
    value: 'local'
  },
  {
    text: t('conflict_dialog.table.headers.remote'),
    sortable: false,
    value: 'remote'
  },
  {
    text: t('conflict_dialog.table.headers.keep'),
    value: 'keep',
    align: 'center',
    sortable: false,
    class: 'conflict-dialog__action-container'
  }
]);

const resolution: Ref<ConflictResolution> = ref({});
const resolutionLength = computed(() => Object.keys(get(resolution)).length);

const setResolution = (strategy: ConflictResolutionStrategy) => {
  const length = get(conflicts).length;
  const resolutionStrategy: Writeable<ConflictResolution> = {};
  for (let i = 0; i < length; i++) {
    const conflict = get(conflicts)[i];
    resolutionStrategy[conflict.identifier] = strategy;
  }

  set(resolution, resolutionStrategy);
};

type AssetKey = keyof SupportedAsset;

const getConflictFields = (conflict: AssetUpdateConflictResult): AssetKey[] => {
  function nonNull(key: AssetKey, asset: SupportedAsset): boolean {
    return asset[key] !== null;
  }
  const remote = Object.keys(conflict.remote).filter(value =>
    nonNull(value as AssetKey, conflict.remote)
  );
  const local = Object.keys(conflict.local).filter(value =>
    nonNull(value as AssetKey, conflict.local)
  );
  return [...remote, ...local].filter(uniqueStrings) as AssetKey[];
};

const isDiff = (conflict: AssetUpdateConflictResult, field: AssetKey) => {
  const localElement = conflict.local[field];
  const remoteElement = conflict.remote[field];
  return localElement !== remoteElement;
};

const remaining = computed(() => {
  const resolved = get(resolutionLength);
  return get(conflicts).length - resolved;
});

const valid = computed(() => {
  const identifiers = get(conflicts)
    .map(({ identifier }) => identifier)
    .sort();
  const resolved = Object.keys(get(resolution)).sort();
  if (identifiers.length !== resolved.length) {
    return false;
  }

  for (const [i, element] of resolved.entries()) {
    if (element !== identifiers[i]) {
      return false;
    }
  }
  return true;
});

const resolve = (resolution: ConflictResolution) => {
  emit('resolve', resolution);
};

const cancel = () => {
  emit('cancel');
};
</script>

<template>
  <BigDialog
    :display="true"
    :title="t('conflict_dialog.title')"
    :subtitle="t('conflict_dialog.subtitle')"
    :action-disabled="!valid"
    max-width="1200px"
    :persistent="resolutionLength > 0"
    @click="resolve(resolution)"
    @cancel="cancel()"
  >
    <div
      class="flex justify-end items-center gap-8 border border-default rounded p-4"
    >
      {{ t('conflict_dialog.all_buttons_description') }}
      <RuiButtonGroup color="primary" variant="outlined">
        <template #default>
          <RuiButton value="local" @click="setResolution('local')">
            {{ t('conflict_dialog.keep_local') }}
          </RuiButton>
          <RuiButton value="remote" @click="setResolution('remote')">
            {{ t('conflict_dialog.keep_remote') }}
          </RuiButton>
        </template>
      </RuiButtonGroup>
    </div>

    <div class="text-caption pt-4 pb-1">
      <i18n path="conflict_dialog.hint" tag="span">
        <template #conflicts>
          <span class="font-medium"> {{ conflicts.length }} </span>
        </template>
        <template #remaining>
          <span class="font-medium"> {{ remaining }} </span>
        </template>
      </i18n>
    </div>

    <DataTable
      :class="{
        [$style.mobile]: true
      }"
      :items="conflicts"
      :headers="tableHeaders"
      disable-floating-header
    >
      <template #item.local="{ item: conflict }">
        <AssetConflictRow
          v-for="field in getConflictFields(conflict)"
          :key="`local-${field}`"
          :field="field"
          :value="conflict.local[field]"
          :diff="isDiff(conflict, field)"
        />
      </template>
      <template #item.remote="{ item: conflict }">
        <AssetConflictRow
          v-for="field in getConflictFields(conflict)"
          :key="`remote-${field}`"
          :field="field"
          :value="conflict.remote[field]"
          :diff="isDiff(conflict, field)"
        />
      </template>
      <template #item.keep="{ item: conflict }">
        <RuiButtonGroup
          v-model="resolution[conflict.identifier]"
          color="primary"
          variant="outlined"
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
    </DataTable>
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
