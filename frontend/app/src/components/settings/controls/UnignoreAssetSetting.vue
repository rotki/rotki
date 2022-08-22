<template>
  <v-row no-gutters>
    <v-col>
      <asset-select
        v-model="assetToRemove"
        outlined
        show-ignored
        :label="$tc('account_settings.asset_settings.labels.unignore')"
        :items="ignoredAssets"
        :success-messages="success"
        :error-messages="error"
        :hint="$tc('account_settings.asset_settings.labels.unignore_hint')"
        class="accounting-settings__ignored-assets"
      />
    </v-col>
    <v-col cols="auto" class="ml-4">
      <v-btn
        width="110px"
        class="accounting-settings__buttons__remove mt-3"
        text
        color="primary"
        :disabled="assetToRemove === ''"
        @click="removeAsset()"
      >
        {{ $tc('common.actions.remove') }}
      </v-btn>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { defineComponent, ref } from 'vue';
import { useClearableMessages } from '@/composables/settings';
import i18n from '@/i18n';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';

export default defineComponent({
  name: 'UnignoreAssetSetting',
  setup() {
    const assetToRemove = ref('');
    const { error, success, clear, wait, stop, setSuccess, setError } =
      useClearableMessages();
    const { getAssetSymbol } = useAssetInfoRetrieval();
    const store = useIgnoredAssetsStore();
    const { ignoredAssets } = storeToRefs(store);
    const { unignoreAsset } = store;

    async function removeAsset() {
      stop();
      clear();
      const identifier = get(assetToRemove);
      const result = await unignoreAsset(identifier);
      const asset = getAssetSymbol(identifier);

      await wait();
      if (result.success) {
        setSuccess(
          i18n.tc('account_settings.messages.unignored_success', 0, { asset })
        );
        set(assetToRemove, '');
      } else {
        setError(
          i18n.tc('account_settings.messages.unignored_failure', 0, {
            asset,
            message: result.message
          })
        );
      }
    }

    return {
      assetToRemove,
      success,
      error,
      ignoredAssets,
      removeAsset
    };
  }
});
</script>
