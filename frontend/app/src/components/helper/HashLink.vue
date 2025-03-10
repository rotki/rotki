<script setup lang="ts">
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useAddressBookForm } from '@/composables/address-book/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useLinks } from '@/composables/links';
import { useScramble } from '@/composables/scramble';
import { useBlockchainStore } from '@/store/blockchain';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { type ExplorerUrls, explorerUrls, isChains } from '@/types/asset/asset-urls';
import { truncateAddress } from '@/utils/truncate';
import { Blockchain, consistOfNumbers } from '@rotki/common';

interface HashLinkProps {
  showIcon?: boolean;
  text?: string;
  fullAddress?: boolean;
  linkOnly?: boolean;
  noLink?: boolean;
  copyOnly?: boolean;
  baseUrl?: string;
  chain?: string;
  evmChain?: string;
  buttons?: boolean;
  size?: number | string;
  truncateLength?: number;
  type?: keyof ExplorerUrls | 'label';
  disableScramble?: boolean;
  hideAliasName?: boolean;
  location?: string;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<HashLinkProps>(), {
  baseUrl: undefined,
  buttons: false,
  chain: Blockchain.ETH,
  copyOnly: false,
  disableScramble: false,
  evmChain: undefined,
  fullAddress: false,
  hideAliasName: false,
  linkOnly: false,
  location: undefined,
  noLink: false,
  showIcon: true,
  size: 12,
  text: '',
  truncateLength: 4,
  type: 'address',
});

const { t } = useI18n();
const { copy } = useClipboard();

const { baseUrl, chain, disableScramble, evmChain, hideAliasName, location, text, type } = toRefs(props);
const { scrambleAddress, scrambleData, scrambleIdentifier, shouldShowAmount } = useScramble();

const { explorers } = storeToRefs(useFrontendSettingsStore());
const { getChain, getChainInfoByName } = useSupportedChains();
const { accountTags } = useBlockchainStore();

const { addressNameSelector } = useAddressesNamesStore();
const addressName = computed(() => {
  const name = get(location);
  if (name && !get(getChainInfoByName(name)))
    return null;

  return get(addressNameSelector(text, chain));
});

const blockchain = computed(() => {
  if (isDefined(evmChain))
    return getChain(get(evmChain));

  return get(chain);
});

const aliasName = computed<string | null>(() => {
  if (get(hideAliasName) || get(scrambleData) || get(type) !== 'address')
    return null;

  const name = get(addressName);
  if (!name)
    return null;

  return name;
});

const truncatedAliasName = computed<string | null>(() => {
  const alias = get(aliasName);

  if (!alias)
    return alias;

  return truncateAddress(alias, 10);
});

const displayText = computed<string>(() => {
  const linkText = get(text);
  const linkType = get(type);

  if (get(disableScramble))
    return linkText;

  if (linkType === 'block' || consistOfNumbers(linkText))
    return scrambleIdentifier(linkText);

  return scrambleAddress(linkText);
});

const base = computed<string>(() => {
  if (isDefined(baseUrl))
    return get(baseUrl);

  const selectedChain = get(blockchain);
  let base: string | undefined;

  const linkType = get(type);
  if (isChains(selectedChain) && linkType !== 'label') {
    const defaultExplorer: ExplorerUrls = explorerUrls[selectedChain];

    const explorerSetting = get(explorers)[selectedChain];

    if (explorerSetting || defaultExplorer)
      base = explorerSetting?.[linkType] ?? defaultExplorer[linkType];

    // for token missing fallback to address
    if (!base && linkType === 'token')
      base = explorerSetting?.address ?? defaultExplorer.address;
  }

  if (!base)
    return '';
  return base.endsWith('/') ? base : `${base}/`;
});

const url = computed<string>(() => {
  const isToken = get(type) === 'token';
  const linkText = isToken ? get(text).replace('/', '?a=') : get(text);
  return get(base) + linkText;
});

const displayUrl = computed<string>(() => get(base) + truncateAddress(get(text), 10));

const { href, onLinkClick } = useLinks(url);

const { showGlobalDialog } = useAddressBookForm();

const tooltip = ref();

function openAddressBookForm() {
  get(tooltip)?.onClose?.(true);
  showGlobalDialog({
    address: get(text),
    blockchain: get(blockchain),
  });
}

const showAddressBookButton = computed(() => get(type) === 'address' && get(blockchain) !== Blockchain.ETH2);

const tags = computed(() => {
  const address = get(text);
  return get(accountTags(address));
});

const [DefineButton, ReuseButton] = createReusableTemplate();
</script>

<template>
  <DefineButton>
    <RuiButton
      v-if="showAddressBookButton"
      size="sm"
      variant="text"
      class="-my-0.5"
      icon
      @click="openAddressBookForm()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-pencil"
          size="16"
          class="!text-rui-grey-400"
        />
      </template>
    </RuiButton>
  </DefineButton>
  <div
    class="flex flex-row shrink items-center gap-1 text-xs [&_*]:font-mono [&_*]:leading-6"
    v-bind="$attrs"
  >
    <template v-if="showIcon && !linkOnly && type === 'address'">
      <EnsAvatar
        :address="displayText"
        avatar
        size="22px"
      />
    </template>

    <template v-if="!linkOnly && !buttons">
      <span
        v-if="fullAddress"
        :class="{ blur: !shouldShowAmount }"
      >
        {{ displayText }}
      </span>

      <RuiTooltip
        v-else
        ref="tooltip"
        :popper="{ placement: 'top' }"
        :open-delay="400"
        tooltip-class="[&_*]:font-mono"
        persist-on-tooltip-hover
      >
        <template #activator>
          <div :class="{ blur: !shouldShowAmount }">
            <template v-if="truncatedAliasName">
              {{ truncatedAliasName }}
            </template>
            <template v-else>
              {{ truncateAddress(displayText, truncateLength) }}
            </template>
          </div>
        </template>
        <template v-if="tags.length > 0">
          <TagDisplay
            :tags="tags"
            class="!mt-1 mb-2"
            small
          />
        </template>
        <div class="flex items-center gap-2">
          {{ displayText }}

          <ReuseButton v-if="!aliasName" />
        </div>
        <div
          v-if="aliasName"
          class="font-bold flex items-center mt-1 !gap-2"
        >
          {{ aliasName }}

          <ReuseButton />
        </div>
      </RuiTooltip>
    </template>

    <div class="flex items-center gap-1 pl-1">
      <RuiTooltip
        v-if="!linkOnly || buttons"
        :popper="{ placement: 'top' }"
        :open-delay="600"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            class="!bg-rui-grey-200 dark:!bg-rui-grey-900 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
            size="sm"
            color="primary"
            @click="copy(text)"
          >
            <RuiIcon
              name="lu-copy"
              :size="size"
            />
          </RuiButton>
        </template>

        {{ t('common.actions.copy_to_clipboard') }}
      </RuiTooltip>

      <RuiTooltip
        v-if="(linkOnly || !noLink || buttons) && !copyOnly"
        :popper="{ placement: 'top' }"
        :open-delay="600"
      >
        <template #activator>
          <RuiButton
            v-if="!!base"
            tag="a"
            icon
            variant="text"
            class="!bg-rui-grey-200 dark:!bg-rui-grey-900 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
            size="sm"
            color="primary"
            :href="href"
            target="_blank"
            @click="onLinkClick()"
          >
            <RuiIcon
              name="lu-external-link"
              :size="size"
            />
          </RuiButton>
        </template>

        {{ t('hash_link.open_link') }}:
        {{ displayUrl }}
      </RuiTooltip>
    </div>
  </div>
</template>
