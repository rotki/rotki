<script setup lang="ts">
import { type Account, Blockchain } from '@rotki/common';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useScramble } from '@/composables/scramble';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { truncateAddress } from '@/modules/common/display/truncate';

const { account, hideChainIcon = false, noTruncate = false, size = '24px', useAliasName = true } = defineProps<{
  account: Account;
  useAliasName?: boolean;
  noTruncate?: boolean;
  hideChainIcon?: boolean;
  size?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAddressName } = useAddressNameResolution();
const { scrambleAddress, scrambleData, shouldShowAmount } = useScramble();

const address = computed<string>(() => {
  const addr = account.address;
  return scrambleAddress(addr);
});

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
    :popper="{ placement: 'top' }"
    :open-delay="400"
    :disabled="noTruncate && !aliasName"
    class="flex items-center flex-nowrap gap-2"
    tooltip-class="[&_*]:font-mono"
  >
    <template #activator>
      <div
        v-if="!hideChainIcon"
        class="pr-1"
      >
        <div class="rounded-full overflow-hidden w-6 h-6 dark:bg-rui-grey-600 flex items-center justify-center">
          <ChainIcon
            v-if="account.chain && account.chain !== 'ALL'"
            size="22px"
            :chain="account.chain"
          />
          <RuiTooltip
            v-else
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiIcon
                name="lu-link"
                size="16px"
                class="text-rui-text-secondary"
              />
            </template>
            {{ t('common.multi_chain') }}
          </RuiTooltip>
        </div>
      </div>

      <EnsAvatar
        :address="address"
        avatar
        class="mr-2"
        :size="size"
      />

      <div
        :class="{ blur: !shouldShowAmount }"
        class="text-no-wrap [&_*]:font-mono text-xs"
      >
        <div v-if="aliasName">
          {{ aliasName }}
        </div>
        <div v-else>
          {{ !noTruncate ? truncateAddress(address, 6) : address }}
        </div>
      </div>
    </template>
    {{ address }}
  </RuiTooltip>
</template>
