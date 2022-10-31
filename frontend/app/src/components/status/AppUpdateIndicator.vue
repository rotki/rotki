<template>
  <v-tooltip v-if="updateNeeded" bottom>
    <template #activator="{ on }">
      <v-btn text icon @click="update()">
        <v-icon color="error" dark v-on="on"> mdi-arrow-up-bold-circle </v-icon>
      </v-btn>
    </template>
    <span v-text="t('update_indicator.version', { appVersion })" />
  </v-tooltip>
</template>

<script setup lang="ts">
import { useInterop } from '@/electron-interop';
import { useMainStore } from '@/store/main';
import { useSessionStore } from '@/store/session';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { startPromise } from '@/utils';

const mainStore = useMainStore();
const { version, updateNeeded } = storeToRefs(mainStore);
const { getVersion } = mainStore;
const { isPackaged, openUrl } = useInterop();
const { versionUpdateCheckFrequency } = storeToRefs(useFrontendSettingsStore());
const { showUpdatePopup } = storeToRefs(useSessionStore());

const appVersion = computed(() => get(version).latestVersion);

const openLink = () => openUrl(get(version).downloadUrl);
const openUpdatePopup = () => {
  set(showUpdatePopup, true);
};

const update = () => {
  if (isPackaged) {
    openUpdatePopup();
  } else {
    openLink();
  }
};

const period = get(versionUpdateCheckFrequency) * 60 * 60 * 1000;

const { pause, resume, isActive } = useIntervalFn(
  () => {
    startPromise(getVersion());
  },
  period,
  { immediate: false }
);

const setVersionUpdateCheckInterval = () => {
  if (isActive) pause();
  if (period > 0) {
    resume();
  }
};

onMounted(() => {
  setVersionUpdateCheckInterval();
});

watch(versionUpdateCheckFrequency, () => setVersionUpdateCheckInterval());

const { t } = useI18n();
</script>
