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
import { computed, defineComponent, toRefs, watch } from '@vue/composition-api';
import { useInterop } from '@/electron-interop';
import { useMainStore } from '@/store/store';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'AppUpdateIndicator',
  setup() {
    let refreshInterval: any = undefined;
    const mainStore = useMainStore();
    const store = useStore();
    const { version, updateNeeded } = toRefs(mainStore);
    const { getVersion } = mainStore;
    const { isPackaged, openUrl } = useInterop();

    const versionUpdateCheckFrequency = computed(
      () => store.state.settings!.versionUpdateCheckFrequency
    );
    const appVersion = computed(() => version.value.latestVersion);

    const openLink = () => openUrl(version.value.downloadUrl);
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

    const setVersionUpdateCheckInterval = () => {
      clearInterval(refreshInterval);
      const period = versionUpdateCheckFrequency.value * 60 * 60 * 1000;
      if (period > 0) {
        refreshInterval = setInterval(async () => {
          await getVersion();
        }, period);
      }
    };

    setVersionUpdateCheckInterval();

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
