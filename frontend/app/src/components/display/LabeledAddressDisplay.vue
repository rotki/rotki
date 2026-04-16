<script setup lang="ts">
import type {
  BlockchainAccount,
  BlockchainAccountBalance,
} from '@/modules/accounts/blockchain-accounts';
import { consistOfNumbers } from '@rotki/common';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useScramble } from '@/composables/scramble';
import { getAccountAddress, getAccountLabel, getChain, isXpubAccount } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { findAddressKnownPrefix, truncateAddress } from '@/modules/common/display/truncate';
import HashLink from '@/modules/common/links/HashLink.vue';

const { account } = defineProps<{
  account: BlockchainAccount | BlockchainAccountBalance;
}>();
const { scrambleAddress, scrambleData, scrambleIdentifier, shouldShowAmount } = useScramble();
const { getAddressName, getEnsName } = useAddressNameResolution();
const { t } = useI18n({ useScope: 'global' });

const accountAddress = computed<string>(() => getAccountAddress(account));

const derivationPath = computed<string | undefined>(() => {
  if ('xpub' in account.data)
    return account.data.derivationPath;

  return undefined;
});

const isXpub = computed<boolean>(() => 'xpub' in account.data);

const label = computed<string>(() => {
  const label = getAccountLabel(account);

  if (consistOfNumbers(label))
    return scrambleIdentifier(label);

  return label;
});

const aliasName = computed<string>(() => {
  if (get(scrambleData))
    return '';

  const chain = getChain(account);
  const labelVal = get(label);

  if (isXpubAccount(account)) {
    return labelVal;
  }
  const name = getAddressName(get(accountAddress), chain);

  if (!name)
    return labelVal;

  return name;
});

const ensName = computed<string | null>(() => {
  if (get(scrambleData))
    return null;

  return getEnsName(get(accountAddress));
});

const address = computed<string>(() => scrambleAddress(get(accountAddress)));

const displayedLabel = useTemplateRef<HTMLDivElement>('displayedLabel');
const { width: displayedLabelWidth } = useElementSize(displayedLabel);

const labelDisplayed = computed(() => {
  const alias = get(aliasName);
  if (alias)
    return alias;
  return get(address);
});

const CH = 7.21;
const truncatedLabelDisplayed = computed(() => {
  const label = get(labelDisplayed);
  const characterLength = label.length;
  const displayedWidth = get(displayedLabelWidth);
  const charDisplayLimit = Math.floor(displayedWidth / CH);

  if (charDisplayLimit >= characterLength)
    return label;

  const knownPrefix = findAddressKnownPrefix(label);

  const charactersWithinSpace = Math.floor((charDisplayLimit - knownPrefix.length - 3) / 2);
  return truncateAddress(label, charactersWithinSpace);
});
</script>

<template>
  <RuiChip
    variant="outlined"
    class="w-full hover:cursor-default max-w-[32rem] min-w-[15rem] !bg-rui-grey-100 dark:!bg-rui-grey-900"
    content-class="w-full flex items-center px-0"
    size="sm"
    color="primary"
  >
    <RuiTooltip
      :disabled="!shouldShowAmount"
      :popper="{ placement: 'top' }"
      :open-delay="400"
      class="flex-1"
    >
      <template #activator>
        <div
          data-cy="labeled-address-display"
          class="flex items-center gap-2 text-rui-text-secondary w-full"
        >
          <EnsAvatar
            :address="address"
            avatar
          />

          <div
            v-if="isXpub"
            class="font-medium"
          >
            {{ t('common.xpub') }}
          </div>

          <div
            ref="displayedLabel"
            class="flex-1 font-mono overflow-hidden text-xs"
            :class="{ blur: !shouldShowAmount }"
          >
            {{ truncatedLabelDisplayed }}
          </div>
        </div>
      </template>
      <div class="[&_*]:font-mono">
        <div v-if="aliasName && aliasName !== address">
          {{ aliasName }}
        </div>
        <div v-if="ensName && aliasName !== ensName">
          ({{ ensName }})
        </div>
        <div>
          {{ address }}
        </div>
        <div v-if="derivationPath">
          {{ derivationPath }}
        </div>
      </div>
    </RuiTooltip>
    <RuiDivider
      vertical
      class="h-[1.75rem] mx-1 border-black/[.12] dark:border-white/[.12]"
    />
    <div class="flex items-center h-[1.75rem]">
      <HashLink
        class="h-full"
        :text="accountAddress"
        :display-mode="isXpub ? 'copy' : 'default'"
        hide-text
        size="14"
        :location="getChain(account)"
      />
    </div>
  </RuiChip>
</template>
