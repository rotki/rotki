<script setup lang="ts">
import { type Account, Blockchain } from '@rotki/common';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useScramble } from '@/modules/settings/use-scramble';
import { badgeSize } from '@/modules/shell/components/asset-icon-display';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';

const { account, hideAvatar = false, hideChainIcon = false, noTruncate = false, size = '24px', useAliasName = true } = defineProps<{
  account: Account;
  useAliasName?: boolean;
  noTruncate?: boolean;
  hideChainIcon?: boolean;
  /** Leaves the avatar to the caller, such as a chip that shows it in its own leading circle. */
  hideAvatar?: boolean;
  size?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAddressName } = useAddressNameResolution();
const { scrambleAddress, scrambleData, shouldShowAmount } = useScramble();

const address = computed<string>(() => {
  const addr = account.address;
  return scrambleAddress(addr);
});

/** The chain sits as a badge on the avatar's corner, as on asset icons, at half the avatar but never under 10px. */
const chainBadgeSize = computed<string>(() => `${Math.max(10, Number.parseInt(badgeSize(undefined, size, 50)))}px`);

const chainIconSize = computed<string>(() => `${Number.parseInt(get(chainBadgeSize)) - 2}px`);

const aliasName = computed<string | null>(() => {
  if (!get(scrambleData) && useAliasName) {
    const { address, chain } = account;
    const chainId = chain === 'ALL' ? Blockchain.ETH : chain;
    const name = getAddressName(address, chainId);
    if (name)
      return truncateAddress(name, 10);
  }

  return null;
});
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
    :disabled="noTruncate && !aliasName"
    class="flex items-center flex-nowrap gap-2"
    :class-names="{ tooltip: '**:font-mono' }"
  >
    <template #activator>
      <span
        v-if="!hideAvatar"
        class="relative mr-2 inline-flex shrink-0"
      >
        <EnsAvatar
          :address="address"
          avatar
          :size="size"
        />
        <span
          v-if="!hideChainIcon"
          class="absolute -right-1 -bottom-1 z-1 flex items-center justify-center overflow-hidden rounded-full border border-rui-grey-300 bg-white shadow-xs dark:border-rui-grey-900 dark:bg-rui-grey-800"
          :style="{ width: chainBadgeSize, height: chainBadgeSize }"
          data-testid="account-chain-badge"
        >
          <ChainIcon
            v-if="account.chain && account.chain !== 'ALL'"
            :size="chainIconSize"
            :chain="account.chain"
          />
          <RuiTooltip
            v-else
            :options="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiIcon
                name="lu-link"
                :size="chainIconSize"
                class="text-rui-text-secondary"
              />
            </template>
            {{ t('common.multi_chain') }}
          </RuiTooltip>
        </span>
      </span>

      <div
        :class="{ blur: !shouldShowAmount }"
        class="text-no-wrap"
      >
        <div
          v-if="aliasName"
          class="text-sm"
          data-testid="account-name"
        >
          {{ aliasName }}
        </div>
        <div
          v-else
          class="font-mono text-xs"
          data-testid="account-address"
        >
          {{ !noTruncate ? truncateAddress(address, 6) : address }}
        </div>
      </div>
    </template>
    {{ address }}
  </RuiTooltip>
</template>
