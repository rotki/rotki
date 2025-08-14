<script setup lang="ts">
import type { SupportedAsset, Writeable } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { AssetUpdateConflictResult, ConflictResolution } from '@/types/asset';
import type { ConflictResolutionStrategy } from '@/types/common';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import AssetConflictRow from '@/components/status/update/AssetConflictRow.vue';
import { uniqueObjects, uniqueStrings } from '@/utils/data';

const props = defineProps<{
  conflicts: AssetUpdateConflictResult[];
}>();

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'resolve', resolution: ConflictResolution): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const { conflicts } = toRefs(props);

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

const manualResolution = ref(false);
const resolution = ref<ConflictResolution>({});
const strategyModeForAll = ref<ConflictResolutionStrategy>();
const resolutionLength = computed(() => Object.keys(get(resolution)).length);
const activeStrategyForAll = computed(() => {
  if (get(conflicts).length === 0 || get(resolutionLength) !== get(conflicts).length)
    return { local: false, remote: false };

  const strategy = get(strategyModeForAll);

  return { local: strategy === 'local', remote: strategy === 'remote' };
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
  else set(strategyModeForAll, undefined);
}

type AssetKey = keyof SupportedAsset;

function getConflictFields(conflict: AssetUpdateConflictResult): AssetKey[] {
  function nonNull(key: AssetKey, asset: SupportedAsset): boolean {
    return asset[key] !== null;
  }
  const remote = Object.keys(conflict.remote).filter(value => nonNull(value as AssetKey, conflict.remote));
  const local = Object.keys(conflict.local).filter(value => nonNull(value as AssetKey, conflict.local));
  return [...remote, ...local].filter(uniqueStrings) as AssetKey[];
}

function isDiff(conflict: AssetUpdateConflictResult, field: AssetKey) {
  const localElement = conflict.local[field];
  const remoteElement = conflict.remote[field];
  return localElement !== remoteElement;
}

const remaining = computed(() => {
  const resolved = get(resolutionLength);
  return uniqueObjects(get(conflicts), ({ identifier }) => identifier).length - resolved;
});

const warnDuplicate = computed<boolean>(() => {
  const identifiers = get(conflicts)
    .map(({ identifier }) => identifier)
    .sort();
  const uniqueIdentifiers = identifiers.filter(uniqueStrings);
  return identifiers.length > uniqueIdentifiers.length;
});

const duplicateIdentifiers = computed<string[]>(() =>
  get(conflicts)
    .map(({ identifier }) => identifier)
    .sort()
    .filter((e, i, a) => a.indexOf(e) !== i),
);

const valid = computed<boolean>(() => {
  const identifiers = get(conflicts)
    .map(({ identifier }) => identifier)
    .filter(uniqueStrings)
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

function resolve() {
  emit('resolve', get(resolution));
}

function cancel() {
  if (!get(manualResolution)) {
    setResolution('local');
    return resolve();
  }
  emit('cancel');
}

onMounted(() => {
  setResolution('remote');
});
</script>

<template>
  <BigDialog
    :title="t('conflict_dialog.title')"
    :action-disabled="!valid"
    :persistent="resolutionLength > 0"
    :auto-height="!manualResolution"
    :primary-action="!manualResolution ? t('conflict_dialog.keep_remote') : undefined"
    :secondary-action="!manualResolution ? t('conflict_dialog.keep_local') : undefined"
    max-width="75rem"
    display
    divide
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
    <template #default="{ wrapper }">
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
            :popper="{ placement: 'top' }"
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
            :popper="{ placement: 'top' }"
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
              @update:model-value="onStrategyChange(resolution[conflict.identifier])"
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
        data-cy="manage-conflicts"
        color="primary"
        variant="text"
        @click="manualResolution = true"
      >
        {{ t('conflict_dialog.manage') }}
      </RuiButton>
    </template>
  </BigDialog>
</template>
