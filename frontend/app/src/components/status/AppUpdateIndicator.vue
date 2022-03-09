<template>
  <v-tooltip v-if="updateNeeded" bottom>
    <template #activator="{ on }">
      <v-btn text icon @click="update()">
        <v-icon color="error" dark v-on="on"> mdi-arrow-up-bold-circle </v-icon>
      </v-btn>
    </template>
    <span v-text="$t('update_indicator.version', { appVersion })" />
  </v-tooltip>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, useIntervalFn } from '@vueuse/core';
import { useInterop } from '@/electron-interop';
import { useMainStore } from '@/store/store';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'AppUpdateIndicator',
  setup() {
    const mainStore = useMainStore();
    const store = useStore();
    const { version, updateNeeded } = toRefs(mainStore);
    const { getVersion } = mainStore;
    const { isPackaged, openUrl } = useInterop();

    const versionUpdateCheckFrequency = computed(
      () => store.state.settings!.versionUpdateCheckFrequency
    );
    const appVersion = computed(() => get(version).latestVersion);

    const openLink = () => openUrl(get(version).downloadUrl);
    const openUpdatePopup = async () => {
      await store.dispatch('session/openUpdatePopup');
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
        getVersion();
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

    return {
      appVersion,
      updateNeeded,
      openUpdatePopup,
      update,
      openLink
    };
  }
});
</script>
