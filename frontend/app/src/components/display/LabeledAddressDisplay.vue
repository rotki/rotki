<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';
import { getChain } from '@/utils/blockchain/accounts';
import type {
  BlockchainAccount,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

const props = defineProps<{
  account: BlockchainAccount | BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance;
}>();

const { account } = toRefs(props);
const { scrambleData, shouldShowAmount, scrambleHex, scrambleIdentifier } = useScramble();
const { addressNameSelector, ensNameSelector } = useAddressesNamesStore();
const css = useCssModule();
const { t } = useI18n();

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
  const name = get(addressNameSelector(get(accountAddress), chain));

  if (!name)
    return get(label);

  return name;
});

const ensName = computed<string | null>(() => {
  if (get(scrambleData))
    return null;

  return get(ensNameSelector(get(accountAddress)));
});

const { isXs, name } = useBreakpoint();

const address = computed<string>(() => scrambleHex(get(accountAddress)));

const truncationLength = computed<number>(() => {
  let truncationPoint = truncationPoints[get(name)];
  truncationPoint = truncationPoint ?? 4;

  return Math.max(4, truncationPoint);
});

const truncatedAddress = computed<string>(() =>
  truncateAddress(get(address), get(truncationLength)),
);

const truncated = computed<boolean>(() => {
  const truncated = get(truncatedAddress);
  if (truncated.length >= get(address).length)
    return false;

  return truncated.includes('...');
});

const truncatedAliasName = computed<string>(() => {
  const name = get(aliasName);
  if (!name)
    return '';

  const length = get(truncationLength) * 2;

  if (length > 0 && name.length > length)
    return `${name.slice(0, Math.max(0, length))}...`;

  return name;
});
</script>

<template>
  <RuiChip
    variant="outlined"
    :class="css['labeled-address-display']"
    size="sm"
    color="primary"
  >
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
      :disabled="!truncated && !aliasName"
      class="truncate mr-auto"
    >
      <template #activator>
        <span
          data-cy="labeled-address-display"
          :class="[
            css['labeled-address-display__address'],
            { 'labeled-address-display__address--mobile': isXs },
          ]"
        >
          <EnsAvatar
            :address="address"
            avatar
          />

          <span
            v-if="isXpub"
            class="font-medium"
          >
            {{ t('common.xpub') }}
          </span>

          <span
            v-if="aliasName"
            class="text-truncate"
          >
            {{ truncatedAliasName }}
          </span>
          <span
            v-else
            :class="{ blur: !shouldShowAmount }"
          >
            {{ truncatedAddress }}
          </span>
        </span>
      </template>
      <div>
        <div v-if="aliasName && aliasName !== address">
          {{ aliasName }}
        </div>
        <div v-if="ensName && aliasName !== ensName">
          ({{ ensName }})
        </div>
        <div>{{ address }}</div>
        <div v-if="derivationPath">
          {{ derivationPath }}
        </div>
      </div>
    </RuiTooltip>
    <RuiDivider
      vertical
      :class="css['labeled-address-display__divider']"
    />
    <div :class="css['labeled-address-display__actions']">
      <HashLink
        class="h-full"
        :text="accountAddress"
        buttons
        size="14"
        :show-icon="false"
        :chain="getChain(account)"
      />
    </div>
  </RuiChip>
</template>

<style module lang="scss">
.labeled-address-display {
  @apply w-full hover:cursor-default;
  @apply bg-rui-grey-100 #{!important};

  > span {
    @apply w-full flex items-center px-0;
  }

  &__address {
    @apply flex items-center gap-2 text-rui-text-secondary;

    &--mobile {
      @apply max-w-[9.375rem];
    }
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
