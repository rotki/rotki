<script setup lang="ts">
import type {
  BlockchainAccount,
  BlockchainAccountBalance,
} from '@/modules/accounts/blockchain-accounts';
import { consistOfNumbers } from '@rotki/common';
import { getAccountAddress, getAccountLabel, getChain, isXpubAccount } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useScramble } from '@/modules/settings/use-scramble';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';
import { truncateToWidth } from '@/modules/shell/components/display/truncate-to-width';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { account } = defineProps<{
  account: BlockchainAccount | BlockchainAccountBalance;
}>();
const { scrambleAddress, scrambleData, scrambleIdentifier, shouldShowAmount } = useScramble();
const { getAddressName, getEnsName } = useAddressNameResolution();
const { t } = useI18n({ useScope: 'global' });

const accountAddress = computed<string>(() => getAccountAddress(account));

const derivationPath = computed<string | undefined>(() => {
  if (isXpubAccount(account))
    return account.derivationPath;

  return undefined;
});

const isXpub = computed<boolean>(() => isXpubAccount(account));

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

/**
 * A bare address reads best in monospace; a name is set like the rest of the row. An account with
 * no label of its own gets its address as the label, so that counts as an address too.
 */
const showsAddress = computed<boolean>(() => {
  const shown = get(labelDisplayed);
  return shown === get(address) || shown === get(accountAddress);
});

/**
 * An address is cut in the middle, keeping both ends you check it by; a name ends in a CSS
 * ellipsis, since the width estimate assumes the narrow monospace characters of an address.
 */
const truncatedLabelDisplayed = computed<string>(() =>
  get(showsAddress) ? truncateToWidth(get(labelDisplayed), get(displayedLabelWidth)) : get(labelDisplayed),
);
</script>

<template>
  <!--
    Avatar and name, set like the rest of the row rather than as an outlined chip. The explorer or
    copy link shows while the row is hovered or focused, so a table of accounts is not a column of
    buttons.
  -->
  <div class="flex items-center gap-1 w-full max-w-128 min-w-48">
    <RuiTooltip
      :disabled="!shouldShowAmount"
      :options="{ placement: 'top' }"
      :open-delay="400"
      class="flex-1 min-w-0"
    >
      <template #activator>
        <div
          data-testid="labeled-address-display"
          class="flex items-center gap-2 w-full"
        >
          <EnsAvatar
            :address="address"
            avatar
          />

          <div
            v-if="isXpub"
            class="text-body-2 font-medium"
          >
            {{ t('common.xpub') }}
          </div>

          <div
            ref="displayedLabel"
            class="flex-1 truncate text-body-2 font-medium text-rui-text"
            :class="{ 'blur': !shouldShowAmount, 'font-mono text-xs': showsAddress }"
          >
            {{ truncatedLabelDisplayed }}
          </div>
        </div>
      </template>
      <div class="**:font-mono">
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
    <!-- hidden only inside a table row that is neither hovered nor focused; elsewhere it always shows -->
    <div class="flex items-center h-7 transition-opacity [tr:not(:hover)_&:not(:focus-within)]:opacity-0 motion-reduce:transition-none">
      <HashLink
        class="h-full"
        :text="accountAddress"
        :display-mode="isXpub ? 'copy' : 'default'"
        hide-text
        size="14"
        :location="getChain(account)"
      />
    </div>
  </div>
</template>
