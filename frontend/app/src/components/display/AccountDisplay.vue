<script setup lang="ts">
import { type Account, Blockchain } from '@rotki/common';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useScramble } from '@/composables/scramble';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { truncateAddress } from '@/utils/truncate';

const props = withDefaults(defineProps<{
  account: Account;
  useAliasName?: boolean;
  truncate?: boolean;
  hideChainIcon?: boolean;
  size?: string;
}>(), {
  hideChainIcon: false,
  size: '24px',
  truncate: true,
  useAliasName: true,
});

const { account, useAliasName } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const { addressNameSelector } = useAddressesNamesStore();

const { scrambleAddress, scrambleData, shouldShowAmount } = useScramble();

const address = computed<string>(() => {
  const address = get(account).address;
  return scrambleAddress(address);
});

const aliasName = computed<string | null>(() => {
  if (!get(scrambleData) && get(useAliasName)) {
    const { address, chain } = get(account);
    const chainId = chain === 'ALL' ? Blockchain.ETH : chain;
    const name = get(addressNameSelector(address, chainId));
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
    :disabled="!truncate"
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
          {{ truncate ? truncateAddress(address, 6) : address }}
        </div>
      </div>
    </template>
    {{ account.address }}
  </RuiTooltip>
</template>
