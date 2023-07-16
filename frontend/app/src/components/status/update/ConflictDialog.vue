<script setup lang="ts">
import { type SupportedAsset } from '@rotki/common/lib/data';
import { type PropType, type Ref, useListeners } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type Writeable } from '@/types';
import {
  type AssetUpdateConflictResult,
  type ConflictResolution,
  type ConflictResolutionStrategy
} from '@/types/asset';

const props = defineProps({
  conflicts: {
    required: true,
    type: Array as PropType<AssetUpdateConflictResult[]>
  }
});

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'resolve', resolution: ConflictResolution): void;
}>();

const { t } = useI18n();

const { conflicts } = toRefs(props);

const rootAttrs = useAttrs();
const rootListeners = useListeners();

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
  const resolved = Object.keys(get(resolution)).length;
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
  <VBottomSheet v-bind="rootAttrs" persistent width="98%" v-on="rootListeners">
    <Card outlined-body contained no-radius-bottom>
      <template #title>{{ t('conflict_dialog.title') }}</template>
      <template #subtitle>{{ t('conflict_dialog.subtitle') }}</template>
      <template #actions>
        <VRow no-gutters justify="end" align="center">
          <VCol cols="auto">
            <span class="pe-2">
              {{ t('conflict_dialog.all_buttons_description') }}
            </span>
          </VCol>
          <VCol cols="auto">
            <VRow no-gutters justify="end">
              <VBtn text value="local" @click="setResolution('local')">
                {{ t('conflict_dialog.keep_local') }}
              </VBtn>
              <VBtn text value="remote" @click="setResolution('remote')">
                {{ t('conflict_dialog.keep_remote') }}
              </VBtn>
            </VRow>
          </VCol>
        </VRow>
      </template>
      <template #hint>
        <I18n path="conflict_dialog.hint" tag="span">
          <template #conflicts>
            <span class="font-weight-medium"> {{ conflicts.length }} </span>
          </template>
          <template #remaining>
            <span class="font-weight-medium"> {{ remaining }} </span>
          </template>
        </I18n>
      </template>
      <DataTable
        :class="{
          [$style.mobile]: true
        }"
        :items="conflicts"
        :headers="tableHeaders"
      >
        <template #item.local="{ item: conflict }">
          <ConflictRow
            v-for="field in getConflictFields(conflict)"
            :key="`local-${field}`"
            :field="field"
            :value="conflict.local[field]"
            :diff="isDiff(conflict, field)"
          />
        </template>
        <template #item.remote="{ item: conflict }">
          <ConflictRow
            v-for="field in getConflictFields(conflict)"
            :key="`remote-${field}`"
            :field="field"
            :value="conflict.remote[field]"
            :diff="isDiff(conflict, field)"
          />
        </template>
        <template #item.keep="{ item: conflict }">
          <VBtnToggle v-model="resolution[conflict.identifier]">
            <VBtn class="conflict-dialog__action" value="local">
              {{ t('conflict_dialog.action.local') }}
            </VBtn>
            <VBtn class="conflict-dialog__action" value="remote">
              {{ t('conflict_dialog.action.remote') }}
            </VBtn>
          </VBtnToggle>
        </template>
      </DataTable>
      <template #options>
        <div class="conflict-dialog__pagination" />
      </template>
      <template #buttons>
        <VRow no-gutters justify="end">
          <VCol cols="auto">
            <VBtn text @click="cancel()">
              {{ t('common.actions.cancel') }}
            </VBtn>
          </VCol>
          <VCol cols="auto">
            <VBtn
              text
              color="primary"
              :disabled="!valid"
              @click="resolve(resolution)"
            >
              {{ t('common.actions.confirm') }}
            </VBtn>
          </VCol>
        </VRow>
      </template>
    </Card>
  </VBottomSheet>
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
