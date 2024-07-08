<script setup lang="ts">
import {
  Blockchain,
} from '@rotki/common/lib/blockchain';
import { truncateAddress } from '@/utils/truncate';
import type { Account } from '@rotki/common/lib/account';

const props = withDefaults(
  defineProps<{
    account: Account;
    useAliasName?: boolean;
    truncate?: boolean;
    hideChainIcon?: boolean;
  }>(),
  {
    useAliasName: true,
    truncate: true,
    hideChainIcon: false,
  },
);

const { account, useAliasName } = toRefs(props);
const { scrambleData, shouldShowAmount, scrambleAddress } = useScramble();
const { addressNameSelector } = useAddressesNamesStore();

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

const { t } = useI18n();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
    :disabled="!truncate"
    class="flex items-center flex-nowrap"
  >
    <template #activator>
      <div
        v-if="!hideChainIcon"
        class="pr-1"
      >
        <div
          class="rounded-full overflow-hidden w-6 h-6 dark:bg-rui-grey-600 flex items-center justify-center"
        >
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
                name="links-line"
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
      />

      <div
        :class="{ blur: !shouldShowAmount }"
        class="text-no-wrap"
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
