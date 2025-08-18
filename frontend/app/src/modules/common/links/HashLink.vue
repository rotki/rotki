<script setup lang="ts">
import type { RuiTooltip } from '@rotki/ui-library';
import { Blockchain, consistOfNumbers } from '@rotki/common';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useScramble } from '@/composables/scramble';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { type ExplorerUrls, explorerUrls, isChains } from '@/types/asset/asset-urls';
import { isBlockchain } from '@/types/blockchain/chains';
import { truncateAddress } from '@/utils/truncate';
import AddressDeleteButton from './AddressDeleteButton.vue';
import AddressEditButton from './AddressEditButton.vue';
import CopyButton from './CopyButton.vue';
import LinkButton from './LinkButton.vue';

type DisplayMode = 'default' | 'link' | 'copy';

interface HashLinkProps {
  /**
   * This can be an address hash, or a transaction hash, or a validator index, or a block number,
   * or an exchange name, etc.
   */
  text: string;
  /**
   * Determines the display mode for the buttons of the component.
   * The `default` mode will show both the copy and link button unless determined otherwise e.g.
   * - location is not a blockchain.
   * - type does not have an explorer link associated with it
   *
   * The `link` mode will only show the link if the location is a blockchain with a valid explorer link.
   * The `copy` mode will only show a copy button for the user to copy the `text` value.
   *
   * @default default
   */
  displayMode?: DisplayMode;
  /**
   * Hides the text and displays only the buttons as determined by the {@link DisplayMode} setting.
   */
  hideText?: boolean;
  /**
   * The location of an event.
   * It can be an EVM chain or a Blockchain or a plain location.
   * If this is a valid Blockchain, the component will display a link to an explorer unless the component
   * is in `copy` display mode.
   */
  location?: string;
  /**
   * Determines the size of the buttons.
   */
  size?: number | string;
  /**
   * Determines the truncate length for the displayed text.
   * To disable truncation, set the truncate length to `0`.
   * @default 4
   */
  truncateLength?: number;
  /**
   * Determines the type of the explorer link that will be used if the `location` is a valid blockchain.
   * @default address
   */
  type?: keyof ExplorerUrls;
  noScramble?: boolean;
}

const props = withDefaults(defineProps<HashLinkProps>(), {
  displayMode: 'default',
  hideText: false,
  location: undefined,
  noScramble: false,
  size: 12,
  truncateLength: 4,
  type: 'address',
});

const { text } = toRefs(props);

const tooltip = useTemplateRef<InstanceType<typeof RuiTooltip>>('tooltip');

const { explorers } = storeToRefs(useFrontendSettingsStore());
const { useAccountTags } = useBlockchainAccountData();
const { addressNameSelector, addressNameSourceSelector } = useAddressesNamesStore();
const { scrambleAddress, scrambleData, scrambleIdentifier, shouldShowAmount } = useScramble();
const { matchChain } = useSupportedChains();

const blockchain = computed<string | undefined>(() => {
  const location = props.location;
  if (!location) {
    return undefined;
  }
  else if (isBlockchain(location)) {
    return location;
  }
  else {
    return matchChain(location);
  }
});

const showLink = computed<boolean>(() => props.displayMode !== 'copy');
const showCopy = computed<boolean>(() => props.displayMode !== 'link');
/**
 * Icons will only be displayed for non-numerical blockchain addresses when the text is visible.
 */
const showIcon = computed<boolean>(() => {
  if (props.type !== 'address' || props.hideText) {
    return false;
  }

  return !/^[+-]?\d+$/.test(props.text);
});

/**
 * Determines the visibility of the address book edit button.
 * The address book edit button will only be visible for blockchain addresses except ETH2
. */
const addressBookChain = computed<string | undefined>(() => {
  const chain = get(blockchain);
  if (chain !== undefined && props.type === 'address' && chain !== Blockchain.ETH2) {
    return chain;
  }
  return undefined;
});

const canShowAddressInfo = computed<boolean>(() => {
  const isLocationNotBlockchain = props.location && !isDefined(blockchain);
  return (!get(scrambleData) || props.noScramble) && props.type === 'address' && !isLocationNotBlockchain;
});

const aliasName = computed<string | undefined>(() => {
  if (!get(canShowAddressInfo))
    return undefined;

  return get(addressNameSelector(props.text, get(blockchain)));
});

const addressSource = computed<string | undefined>(() => {
  if (!get(canShowAddressInfo))
    return undefined;

  return get(addressNameSourceSelector(props.text, get(blockchain)));
});

const displayText = computed<string>(() => {
  if (props.type !== 'address' && !isDefined(blockchain))
    return props.text;

  const linkText = props.text;

  if (props.noScramble) {
    return linkText;
  }

  const linkType = props.type;

  return linkType === 'block' || consistOfNumbers(linkText)
    ? scrambleIdentifier(linkText)
    : scrambleAddress(linkText);
});

const finalDisplayText = computed<string>(() => {
  const truncateLength = props.truncateLength;
  if (truncateLength === 0) {
    return get(displayText);
  }

  if (isDefined(aliasName)) {
    return truncateAddress(get(aliasName), 10);
  }

  return truncateAddress(get(displayText), truncateLength);
});

const base = computed<string>(() => {
  const selectedChain = get(blockchain);
  let base: string | undefined;

  const linkType = props.type;
  if (selectedChain && isChains(selectedChain)) {
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

const tags = useAccountTags(text);
</script>

<template>
  <div class="flex flex-row shrink items-center gap-1 text-xs [&_*]:font-mono [&_*]:leading-6 min-h-[22px]">
    <EnsAvatar
      v-if="showIcon"
      :address="displayText"
      avatar
      size="22px"
    />

    <RuiTooltip
      v-if="!hideText"
      ref="tooltip"
      :popper="{ placement: 'top' }"
      :open-delay="400"
      :disabled="truncateLength === 0"
      tooltip-class="[&_*]:font-mono"
      persist-on-tooltip-hover
    >
      <template #activator>
        <div :class="{ blur: !shouldShowAmount }">
          {{ finalDisplayText }}
        </div>
      </template>

      <TagDisplay
        v-if="tags.length > 0"
        :tags="tags"
        class="!mt-1 mb-2"
        small
      />

      <div class="flex items-center gap-1">
        <div class="flex flex-col gap-1">
          {{ displayText }}
          <div
            v-if="aliasName"
            class="font-bold"
          >
            {{ aliasName }}
          </div>
        </div>

        <AddressEditButton
          v-if="addressBookChain"
          :text="text"
          :blockchain="addressBookChain"
          class="m-1"
          @open="tooltip?.onClose(true)"
        />

        <AddressDeleteButton
          v-if="aliasName && addressSource"
          :text="text"
          :source="addressSource"
        />
      </div>
    </RuiTooltip>

    <div
      v-if="showLink || showCopy"
      class="flex items-center gap-1 pl-1"
    >
      <CopyButton
        v-if="showCopy"
        :text="text"
        :size="size"
      />

      <LinkButton
        v-if="showLink && base"
        :text="text"
        :base="base"
        :size="size"
        :is-token="type === 'token'"
      />
    </div>
  </div>
</template>
