<template>
  <v-row no-gutters>
    <v-col>
      <asset-select
        v-model="assetToIgnore"
        outlined
        :label="$tc('account_settings.asset_settings.labels.ignore')"
        :success-messages="success"
        :error-messages="error"
        :hint="$tc('account_settings.asset_settings.ignore_tags_hint')"
        class="accounting-settings__asset-to-ignore"
      />
    </v-col>
    <v-col cols="auto" class="ml-4">
      <v-btn
        class="accounting-settings__buttons__add mt-3"
        text
        width="110px"
        color="primary"
        :disabled="assetToIgnore === ''"
        @click="addAsset()"
      >
        {{ $tc('account_settings.asset_settings.actions.add') }}
      </v-btn>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { defineComponent, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useClearableMessages } from '@/composables/settings';
import i18n from '@/i18n';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';

export default defineComponent({
  name: 'IgnoreAssetSetting',
  setup() {
    const assetToIgnore = ref('');
    const { error, success, clear, wait, stop, setSuccess, setError } =
      useClearableMessages();

    const { getAssetSymbol } = useAssetInfoRetrieval();
    const { ignoreAsset } = useIgnoredAssetsStore();

    const addAsset = async () => {
      stop();
      clear();
      const identifier = get(assetToIgnore);
      const result = await ignoreAsset(identifier);
      const asset = getAssetSymbol(identifier);

      await wait();

      if (result.success) {
        setSuccess(
          i18n.tc('account_settings.messages.ignored_success', 0, { asset })
        );
        set(assetToIgnore, '');
      } else {
        setError(
          i18n.tc('account_settings.messages.ignored_failure', 0, {
            asset,
            message: result.message
          })
        );
      }
    };

    return {
      assetToIgnore,
      success,
      error,
      addAsset
    };
  }
});
</script>
