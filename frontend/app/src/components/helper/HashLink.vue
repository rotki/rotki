<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { truncateAddress } from '@/filters';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import {
  type Chains,
  type ExplorerUrls,
  explorerUrls
} from '@/types/asset-urls';
import { randomHex } from '@/utils/data';

const props = withDefaults(
  defineProps<{
    showIcon?: boolean;
    text?: string;
    fullAddress?: boolean;
    linkOnly?: boolean;
    noLink?: boolean;
    baseUrl?: string;
    chain?: Chains;
    tx?: boolean;
    buttons?: boolean;
    small?: boolean;
    truncateLength?: number;
  }>(),
  {
    showIcon: true,
    text: '',
    fullAddress: false,
    linkOnly: false,
    noLink: false,
    baseUrl: '',
    chain: Blockchain.ETH,
    tx: false,
    buttons: false,
    small: false,
    truncateLength: 4
  }
);

const { text, baseUrl, chain, tx } = toRefs(props);

const { scrambleData, shouldShowAmount } = storeToRefs(
  useSessionSettingsStore()
);
const { explorers } = storeToRefs(useFrontendSettingsStore());
const { dark } = useTheme();

const { addressNameSelector } = useAddressesNamesStore();

const ethName = computed<string | null>(() => {
  if (!get(scrambleData) || get(tx)) {
    return get(addressNameSelector(text, chain));
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
  let formattedBaseUrl = '';
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

const { getBlockie } = useBlockie();
</script>

<template>
  <div class="d-flex flex-row shrink align-center">
    <span>
      <v-avatar v-if="showIcon && !tx" size="21" class="mr-2">
        <v-img :src="getBlockie(displayText)" />
      </v-avatar>
    </span>
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

<style scoped lang="scss">
.blur-content {
  filter: blur(0.3em);
}
</style>
