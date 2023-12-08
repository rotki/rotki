<script setup lang="ts">
import { type Ref } from 'vue';
import { type AssetVersionUpdate } from '@/types/asset';

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

const partial: Ref<boolean> = ref(false);
const upToVersion: Ref<number> = ref(0);
const skipUpdate: Ref<boolean> = ref(false);

const multiple = computed(() => {
  const { remote, local } = get(versions);
  return remote - local > 1;
});

const onChange = (value: string) => {
  const number = Number.parseInt(value);
  const update = get(versions);
  const { local, remote } = update;
  let updatedUpToVersion: number = number;
  if (isNaN(number)) {
    updatedUpToVersion = local + 1;
  } else if (number < local) {
    updatedUpToVersion = local + 1;
  } else if (number > remote) {
    updatedUpToVersion = remote;
  }
  setUpdateVersion(updatedUpToVersion);
};

const setUpdateVersion = (version: number) => {
  set(upToVersion, version);
  const update = get(versions);

  emit('update:versions', {
    ...update,
    upToVersion: version
  });
};

watch(partial, partial => {
  if (!partial) {
    const remoteVersion = get(versions).remote;
    setUpdateVersion(remoteVersion);
  }
});

onMounted(() => {
  set(upToVersion, get(versions).upToVersion);
});

const { t } = useI18n();
</script>

<template>
  <RuiCard variant="flat" :class="{ 'bg-transparent': headless }">
    <template #header> {{ t('asset_update.title') }} </template>
    <i18n class="text-body-1" tag="div" path="asset_update.description">
      <template #remote>
        <span class="font-medium">{{ versions.remote }}</span>
      </template>
      <template #local>
        <span class="font-medium">{{ versions.local }}</span>
      </template>
    </i18n>
    <div class="text-body-1 mt-4">
      {{ t('asset_update.total_changes', { changes: versions.changes }) }}
    </div>

    <div v-if="multiple" class="font-medium text-body-1 mt-6">
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
          :value="upToVersion"
          variant="outlined"
          color="primary"
          type="number"
          dense
          hide-details
          :min="versions.local"
          :max="versions.remote"
          :label="t('asset_update.up_to_version')"
          @input="onChange($event)"
        />
      </div>
    </div>
    <div v-if="headless">
      <RuiCheckbox v-model="skipUpdate" dense color="primary">
        {{ t('asset_update.skip_notification') }}
      </RuiCheckbox>
    </div>
    <template #footer>
      <div class="grow" />
      <RuiButton
        variant="text"
        color="primary"
        @click="emit('dismiss', skipUpdate)"
      >
        {{ t('common.actions.skip') }}
      </RuiButton>
      <RuiButton color="primary" @click="emit('confirm')">
        {{ t('common.actions.update') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
