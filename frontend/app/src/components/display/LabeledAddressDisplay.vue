<script setup lang="ts">
import type {
  BlockchainAccount,
  BlockchainAccountBalance,
} from '@/types/blockchain/accounts';
import { consistOfNumbers } from '@rotki/common';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useScramble } from '@/composables/scramble';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { getAccountAddress, getAccountLabel, getChain } from '@/utils/blockchain/accounts/utils';
import { findAddressKnownPrefix, truncateAddress } from '@/utils/truncate';

const props = defineProps<{
  account: BlockchainAccount | BlockchainAccountBalance;
}>();

const { account } = toRefs(props);
const { scrambleAddress, scrambleData, scrambleIdentifier, shouldShowAmount } = useScramble();
const { addressNameSelector, ensNameSelector } = useAddressesNamesStore();
const { t } = useI18n({ useScope: 'global' });

const accountAddress = computed<string>(() => getAccountAddress(get(account)));

const derivationPath = computed<string | undefined>(() => {
  const accountInfo = get(account);
  if ('xpub' in accountInfo.data)
    return accountInfo.data.derivationPath;

  return undefined;
});

const isXpub = computed<boolean>(() => {
  const accountInfo = get(account);
  return 'xpub' in accountInfo.data;
});

const label = computed<string>(() => {
  const label = getAccountLabel(get(account));

  if (consistOfNumbers(label))
    return scrambleIdentifier(label);

  return label;
});

const aliasName = computed<string>(() => {
  if (get(scrambleData))
    return '';

  const accountData = get(account);
  const chain = getChain(accountData);
  const labelVal = get(label);

  if (accountData.data.type === 'xpub') {
    return labelVal;
  }
  const name = get(addressNameSelector(get(accountAddress), chain));

  if (!name)
    return labelVal;

  return name;
});

const ensName = computed<string | null>(() => {
  if (get(scrambleData))
    return null;

  return get(ensNameSelector(get(accountAddress)));
});

const address = computed<string>(() => scrambleAddress(get(accountAddress)));

const displayedLabel = ref<HTMLDivElement>();
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
    :class="$style['labeled-address-display']"
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
          :class="[$style['labeled-address-display__address']]"
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
      :class="$style['labeled-address-display__divider']"
    />
    <div :class="$style['labeled-address-display__actions']">
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

<style module lang="scss">
.labeled-address-display {
  @apply w-full hover:cursor-default max-w-[32rem] min-w-[15rem];
  @apply bg-rui-grey-100 #{!important};

  > span {
    @apply w-full flex items-center px-0;
  }

  &__address {
    @apply flex items-center gap-2 text-rui-text-secondary w-full;
  }

  &__divider {
    @apply h-[1.75rem] mx-1 border-black/[.12] dark:border-white/[.12];
  }

  &__actions {
    @apply flex items-center h-[1.75rem];
  }
}

:global(.dark) {
  .labeled-address-display {
    @apply bg-rui-grey-900 #{!important};
  }
}
</style>
