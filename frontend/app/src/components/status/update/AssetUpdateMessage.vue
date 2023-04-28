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

const { tc } = useI18n();
</script>

<template>
  <card :flat="headless">
    <template #title>{{ tc('asset_update.title') }}</template>
    <i18n class="text-body-1" tag="div" path="asset_update.description">
      <template #remote>
        <span class="font-weight-medium">{{ versions.remote }}</span>
      </template>
      <template #local>
        <span class="font-weight-medium">{{ versions.local }}</span>
      </template>
    </i18n>
    <div class="text-body-1 mt-4">
      {{ tc('asset_update.total_changes', 0, { changes: versions.changes }) }}
    </div>

    <div v-if="multiple" class="font-weight-medium text-body-1 mt-4">
      {{ tc('asset_update.advanced') }}
    </div>
    <v-row v-if="multiple">
      <v-col>
        <v-checkbox
          v-model="partial"
          class="asset-update__partial"
          dense
          hide-details
          :label="tc('asset_update.partially_update')"
        />
        <v-col cols="6" class="pa-0 ml-8 mt-2 mb-2">
          <v-text-field
            :disabled="!partial"
            :value="upToVersion"
            outlined
            type="number"
            dense
            hide-details
            :min="versions.local"
            :max="versions.remote"
            :label="tc('asset_update.up_to_version')"
            @change="onChange($event)"
          />
        </v-col>
      </v-col>
    </v-row>
    <template #options>
      <v-checkbox
        v-if="headless"
        v-model="skipUpdate"
        dense
        :label="tc('asset_update.skip_notification')"
      />
    </template>
    <template #buttons>
      <v-row justify="end" no-gutters>
        <v-col cols="auto" class="mr-2">
          <v-btn text @click="emit('dismiss', skipUpdate)">
            {{ tc('common.actions.skip') }}
          </v-btn>
        </v-col>
        <v-col cols="auto">
          <v-btn color="primary" depressed @click="emit('confirm')">
            {{ tc('common.actions.update') }}
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </card>
</template>
