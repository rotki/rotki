<script setup lang="ts">
import type { AssetVersionUpdate } from '@/types/asset';

const props = defineProps<{
  headless: boolean;
  versions: AssetVersionUpdate;
}>();

const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'dismiss', skipUpdate: boolean): void;
  (e: 'update:versions', versions: AssetVersionUpdate): void;
}>();

const { versions } = toRefs(props);

const partial = ref<boolean>(false);
const upToVersion = ref<string>('0');
const skipUpdate = ref<boolean>(false);
const showAdvanced = ref<boolean>(false);

const multiple = computed(() => {
  const { local, remote } = get(versions);
  return remote - local > 1;
});

function onChange(value: string) {
  const number = Number.parseInt(value);
  const update = get(versions);
  const { local, remote } = update;
  let updatedUpToVersion: number = number;
  if (isNaN(number))
    updatedUpToVersion = local + 1;
  else if (number < local)
    updatedUpToVersion = local + 1;
  else if (number > remote)
    updatedUpToVersion = remote;

  setUpdateVersion(updatedUpToVersion);
}

function setUpdateVersion(version: number) {
  set(upToVersion, version.toString());
  const update = get(versions);

  emit('update:versions', {
    ...update,
    upToVersion: version,
  });
}

watch(partial, (partial) => {
  if (!partial) {
    const remoteVersion = get(versions).remote;
    setUpdateVersion(remoteVersion);
  }
});

onMounted(() => {
  set(upToVersion, get(versions).upToVersion.toString());
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <RuiCard
      variant="flat"
      :class="{ 'bg-transparent': headless }"
    >
      <template #header>
        {{ t('asset_update.title') }}
      </template>
      <i18n-t
        scope="global"
        class="text-body-1"
        tag="div"
        keypath="asset_update.description"
      >
        <template #remote>
          <span class="font-medium">{{ versions.remote }}</span>
        </template>
        <template #local>
          <span class="font-medium">{{ versions.local }}</span>
        </template>
      </i18n-t>
      <div class="text-body-1 mt-4">
        {{ t('asset_update.total_changes', { changes: versions.changes }) }}
      </div>

      <RuiAccordion
        :open="showAdvanced"
        class="pt-4 -mx-4 [&>div]:px-4"
      >
        <div class="font-medium text-body-1 border-t border-default pt-4">
          {{ t('asset_update.advanced') }}
        </div>
        <div v-if="multiple">
          <RuiCheckbox
            v-model="partial"
            class="asset-update__partial"
            hide-details
            color="primary"
          >
            {{ t('asset_update.partially_update') }}
          </RuiCheckbox>
          <div class="ml-8 md:w-1/2">
            <RuiTextField
              :disabled="!partial"
              :model-value="upToVersion"
              variant="outlined"
              color="primary"
              type="number"
              dense
              hide-details
              :min="versions.local"
              :max="versions.remote"
              :label="t('asset_update.up_to_version')"
              @update:model-value="onChange($event)"
            />
          </div>
        </div>

        <div v-if="headless">
          <RuiCheckbox
            v-model="skipUpdate"
            dense
            color="primary"
            hide-details
          >
            {{ t('asset_update.skip_notification') }}
          </RuiCheckbox>
        </div>
      </RuiAccordion>

      <template #footer>
        <RuiButton
          v-if="showAdvanced"
          variant="text"
          color="error"
          @click="emit('dismiss', skipUpdate)"
        >
          {{ t('common.actions.skip') }}
        </RuiButton>
        <div class="grow" />

        <RuiButton
          variant="text"
          color="primary"
          @click="showAdvanced = !showAdvanced"
        >
          <template #prepend>
            <RuiIcon
              name="lu-chevron-down"
              size="16"
              class="transition-all"
              :class="{ 'rotate-180': showAdvanced }"
            />
          </template>
          {{ showAdvanced ? t('asset_update.hide_advanced') : t('asset_update.show_advanced') }}
        </RuiButton>
        <RuiButton
          color="primary"
          @click="emit('confirm')"
        >
          {{ t('common.actions.update') }}
        </RuiButton>
      </template>
    </RuiCard>
  </div>
</template>
