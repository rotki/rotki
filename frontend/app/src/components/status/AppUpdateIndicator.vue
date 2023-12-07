<script setup lang="ts">
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
  if (isActive) {
    pause();
  }
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

<template>
  <RuiTooltip v-if="updateNeeded" :open-delay="400">
    <template #activator>
      <RuiButton color="info" icon @click="update()">
        <RuiIcon name="arrow-up-circle-line" />
      </RuiButton>
    </template>
    {{ t('update_indicator.version', { appVersion }) }}
  </RuiTooltip>
</template>
