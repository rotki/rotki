<template>
  <div class="d-flex flex-row shrink align-center">
    <v-avatar v-if="showIcon" size="24" class="mr-2">
      <v-img :src="makeBlockie(displayText)" />
    </v-avatar>
    <span v-if="!linkOnly && !buttons">
      <span v-if="fullAddress" :class="{ 'blur-content': !shouldShowAmount }">
        {{ displayText }}
      </span>
      <v-tooltip v-else top open-delay="400">
        <template #activator="{ on, attrs }">
          <span
            :class="{ 'blur-content': !shouldShowAmount }"
            v-bind="attrs"
            v-on="on"
          >
            <span v-if="ethName">{{ ethName }}</span>
            <span v-else>
              {{ truncateAddress(displayText, truncateLength) }}
            </span>
          </span>
        </template>
        <span> {{ displayText }} </span>
      </v-tooltip>
    </span>
    <v-tooltip v-if="!linkOnly || buttons" top open-delay="600">
      <template #activator="{ on, attrs }">
        <v-btn
          :x-small="!small"
          :small="small"
          icon
          v-bind="attrs"
          :width="!small ? '20px' : null"
          color="primary"
          class="ml-2"
          :class="dark ? null : 'grey lighten-4'"
          v-on="on"
          @click="copyText(text)"
        >
          <v-icon :x-small="!small" :small="small"> mdi-content-copy </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('common.actions.copy') }}</span>
    </v-tooltip>
    <v-tooltip v-if="!noLink || buttons" top open-delay="600" max-width="550">
      <template #activator="{ on, attrs }">
        <v-btn
          v-if="!!base"
          :x-small="!small"
          :small="small"
          icon
          v-bind="attrs"
          :width="!small ? '20px' : null"
          color="primary"
          class="ml-1"
          :class="dark ? null : 'grey lighten-4'"
          :href="href"
          :target="target"
          v-on="on"
          @click="openLink()"
        >
          <v-icon :x-small="!small" :small="small"> mdi-launch </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('hash_link.open_link', { url }) }}</span>
    </v-tooltip>
  </div>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get, useClipboard } from '@vueuse/core';
import makeBlockie from 'ethereum-blockies-base64';
import { storeToRefs } from 'pinia';
import {
  Chains,
  ExplorerUrls,
  explorerUrls
} from '@/components/helper/asset-urls';
import { useTheme } from '@/composables/common';
import { interop } from '@/electron-interop';
import { truncateAddress } from '@/filters';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { randomHex } from '@/utils/data';

export default defineComponent({
  name: 'HashLink',
  props: {
    showIcon: { required: false, type: Boolean, default: false },
    text: { required: false, type: String, default: '' },
    fullAddress: { required: false, type: Boolean, default: false },
    linkOnly: { required: false, type: Boolean, default: false },
    noLink: { required: false, type: Boolean, default: false },
    baseUrl: { required: false, type: String, default: '' },
    chain: {
      required: false,
      type: String as PropType<Chains>,
      default: Blockchain.ETH
    },
    tx: { required: false, type: Boolean, default: false },
    buttons: { required: false, type: Boolean, default: false },
    small: { required: false, type: Boolean, default: false },
    truncateLength: { required: false, type: Number, default: 4 }
  },
  setup(props) {
    const { text, baseUrl, chain, tx } = toRefs(props);

    const { scrambleData, shouldShowAmount } = storeToRefs(
      useSessionSettingsStore()
    );
    const { explorers } = storeToRefs(useFrontendSettingsStore());
    const { dark } = useTheme();

    const { ethNameSelector } = useEthNamesStore();

    const ethName = computed<string | null>(() => {
      if (!get(scrambleData) || get(tx)) {
        return get(ethNameSelector(get(text)));
      }

      return null;
    });

    const displayText = computed<string>(() => {
      if (!get(scrambleData)) {
        return get(text);
      }
      const length = get(tx) ? 64 : 40;
      return randomHex(length);
    });

    const base = computed<string>(() => {
      if (get(baseUrl)) {
        return get(baseUrl);
      }

      const defaultSetting: ExplorerUrls = explorerUrls[get(chain)];
      let formattedBaseUrl: string = '';
      if (get(chain) === 'zksync') {
        formattedBaseUrl = get(tx)
          ? defaultSetting.transaction
          : defaultSetting.address;
      } else {
        const explorersSetting =
          get(explorers)[get(chain) as Exclude<Chains, 'zksync'>];

        if (explorersSetting || defaultSetting) {
          formattedBaseUrl = get(tx)
            ? explorersSetting?.transaction ?? defaultSetting.transaction
            : explorersSetting?.address ?? defaultSetting.address;
        }
      }

      if (!formattedBaseUrl) return '';

      return formattedBaseUrl.endsWith('/')
        ? formattedBaseUrl
        : `${formattedBaseUrl}/`;
    });

    const copyText = (text: string) => {
      const { copy } = useClipboard({ source: text });
      copy();
    };

    const url = computed<string>(() => {
      return get(base) + get(text);
    });

    const href = computed<string | undefined>(() => {
      if (interop.isPackaged) {
        return undefined;
      }

      return get(url);
    });

    const target = computed<string | undefined>(() => {
      if (interop.isPackaged) {
        return undefined;
      }

      return '_blank';
    });

    const openLink = () => {
      interop.openUrl(get(url));
    };

    return {
      ethName,
      makeBlockie,
      url,
      truncateAddress,
      shouldShowAmount,
      base,
      displayText,
      copyText,
      href,
      target,
      openLink,
      dark
    };
  }
});
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.3em);
}
</style>
