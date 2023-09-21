<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { truncateAddress } from '@/utils/truncate';
import {
  type Chains,
  type ExplorerUrls,
  explorerUrls
} from '@/types/asset/asset-urls';

const props = withDefaults(
  defineProps<{
    showIcon?: boolean;
    text?: string;
    fullAddress?: boolean;
    linkOnly?: boolean;
    noLink?: boolean;
    baseUrl?: string;
    chain?: Chains;
    evmChain?: string;
    buttons?: boolean;
    small?: boolean;
    truncateLength?: number;
    type?: keyof ExplorerUrls;
    disableScramble?: boolean;
  }>(),
  {
    showIcon: true,
    text: '',
    fullAddress: false,
    linkOnly: false,
    noLink: false,
    baseUrl: undefined,
    chain: Blockchain.ETH,
    evmChain: undefined,
    buttons: false,
    small: false,
    truncateLength: 4,
    type: 'address',
    disableScramble: false
  }
);
const { t } = useI18n();
const { copy } = useClipboard();

const { text, baseUrl, chain, evmChain, type, disableScramble } = toRefs(props);
const { scrambleData, shouldShowAmount, scrambleHex, scrambleIdentifier } =
  useScramble();

const { explorers } = storeToRefs(useFrontendSettingsStore());
const { dark } = useTheme();
const { getChain } = useSupportedChains();

const { addressNameSelector } = useAddressesNamesStore();
const addressName = addressNameSelector(text, chain);

const blockchain = computed(() => {
  if (isDefined(evmChain)) {
    return getChain(get(evmChain));
  }
  return get(chain);
});

const aliasName = computed<string | null>(() => {
  if (get(scrambleData) || get(type) !== 'address') {
    return null;
  }

  const name = get(addressName);
  if (!name) {
    return null;
  }

  return truncateAddress(name, 10);
});

const displayText = computed<string>(() => {
  const linkText = get(text);
  const linkType = get(type);

  if (get(disableScramble)) {
    return linkText;
  }

  if (linkType === 'block' || consistOfNumbers(linkText)) {
    return scrambleIdentifier(linkText);
  }

  return scrambleHex(linkText);
});

const base = computed<string>(() => {
  if (isDefined(baseUrl)) {
    return get(baseUrl);
  }

  const selectedChain = get(blockchain);
  const defaultExplorer: ExplorerUrls = explorerUrls[selectedChain];
  const linkType = get(type);
  let base: string | undefined = undefined;

  if (selectedChain === 'zksync') {
    base = defaultExplorer[linkType];
  } else {
    const explorerSetting = get(explorers)[selectedChain];

    if (explorerSetting || defaultExplorer) {
      base = explorerSetting?.[linkType] ?? defaultExplorer[linkType];
    }
  }

  if (!base) {
    return '';
  }

  return base.endsWith('/') ? base : `${base}/`;
});

const url = computed<string>(() => get(base) + get(text));

const displayUrl = computed<string>(
  () => get(base) + truncateAddress(get(text), 10)
);

const { href, onLinkClick } = useLinks(url);
</script>

<template>
  <div class="flex flex-row shrink items-center gap-1">
    <span v-if="showIcon && !linkOnly && type === 'address'" class="flex">
      <VAvatar size="22" class="mr-2">
        <EnsAvatar :address="displayText" />
      </VAvatar>
    </span>
    <span v-if="!linkOnly && !buttons">
      <span v-if="fullAddress" :class="{ 'blur-content': !shouldShowAmount }">
        {{ displayText }}
      </span>
      <VTooltip v-else top open-delay="400">
        <template #activator="{ on, attrs }">
          <span
            :class="{ 'blur-content': !shouldShowAmount }"
            v-bind="attrs"
            v-on="on"
          >
            <span v-if="aliasName">{{ aliasName }}</span>
            <span v-else>
              {{ truncateAddress(displayText, truncateLength) }}
            </span>
          </span>
        </template>
        <span> {{ displayText }} </span>
      </VTooltip>
    </span>
    <div class="flex items-center gap-1 pl-1">
      <VTooltip v-if="!linkOnly || buttons" top open-delay="600">
        <template #activator="{ on, attrs }">
          <VBtn
            :x-small="!small"
            :small="small"
            icon
            v-bind="attrs"
            :width="!small ? '20px' : null"
            color="primary"
            :class="dark ? null : 'grey lighten-4'"
            v-on="on"
            @click="copy(text)"
          >
            <VIcon :x-small="!small" :small="small"> mdi-content-copy </VIcon>
          </VBtn>
        </template>
        <span>{{ t('common.actions.copy') }}</span>
      </VTooltip>
      <VTooltip v-if="linkOnly || !noLink || buttons" top open-delay="600">
        <template #activator="{ on, attrs }">
          <VBtn
            v-if="!!base"
            :x-small="!small"
            :small="small"
            icon
            v-bind="attrs"
            :width="!small ? '20px' : null"
            color="primary"
            :class="dark ? null : 'grey lighten-4'"
            :href="href"
            target="_blank"
            v-on="on"
            @click="onLinkClick()"
          >
            <VIcon :x-small="!small" :small="small"> mdi-launch </VIcon>
          </VBtn>
        </template>
        <div>
          <div>{{ t('hash_link.open_link') }}:</div>
          <div>{{ displayUrl }}</div>
        </div>
      </VTooltip>
    </div>
  </div>
</template>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.3em);
}
</style>
