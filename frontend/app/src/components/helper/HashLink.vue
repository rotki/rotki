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
      <span>{{ t('common.actions.copy') }}</span>
    </v-tooltip>
    <v-tooltip v-if="!noLink || buttons" top open-delay="600">
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
          target="_blank"
          v-on="on"
          @click="onLinkClick()"
        >
          <v-icon :x-small="!small" :small="small"> mdi-launch </v-icon>
        </v-btn>
      </template>
      <div>
        <div>{{ t('hash_link.open_link') }}:</div>
        <div>{{ displayUrl }}</div>
      </div>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import makeBlockie from 'ethereum-blockies-base64';
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';
import { useLinks } from '@/composables/links';
import { truncateAddress } from '@/filters';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { Chains, ExplorerUrls, explorerUrls } from '@/types/asset-urls';
import { randomHex } from '@/utils/data';

const props = defineProps({
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
});

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

const copyText = async (text: string) => {
  const { copy } = useClipboard({ source: text });
  await copy();
};

const url = computed<string>(() => {
  return get(base) + get(text);
});

const displayUrl = computed<string>(() => {
  return get(base) + truncateAddress(get(text), 10);
});

const { t } = useI18n();
const { href, onLinkClick } = useLinks(url);
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.3em);
}
</style>
