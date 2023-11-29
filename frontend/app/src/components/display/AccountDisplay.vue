<script setup lang="ts">
import { type Account } from '@rotki/common/lib/account';
import {
  Blockchain,
  type BlockchainSelection
} from '@rotki/common/lib/blockchain';
import { truncateAddress } from '@/utils/truncate';

const props = withDefaults(
  defineProps<{
    account: Account<BlockchainSelection>;
    useAliasName?: boolean;
    truncate?: boolean;
    hideChainIcon?: boolean;
  }>(),
  {
    useAliasName: true,
    truncate: true,
    hideChainIcon: false
  }
);

const { account, useAliasName } = toRefs(props);
const { scrambleData, shouldShowAmount, scrambleHex } = useScramble();
const { addressNameSelector } = useAddressesNamesStore();

const address = computed<string>(() => {
  const address = get(account).address;
  return scrambleHex(address);
});

const aliasName = computed<string | null>(() => {
  if (!get(scrambleData) && get(useAliasName)) {
    const { address, chain } = get(account);
    const chainId = chain === 'ALL' ? Blockchain.ETH : chain;
    const name = get(addressNameSelector(address, chainId));
    if (name) {
      return truncateAddress(name, 10);
    }
  }

  return null;
});

const { t } = useI18n();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    open-delay="400"
    :disabled="!truncate"
    class="flex items-center flex-nowrap"
  >
    <template #activator>
      <div v-if="!hideChainIcon" class="pr-1">
        <VAvatar left size="28px">
          <ChainIcon
            v-if="account.chain && account.chain !== 'ALL'"
            size="24px"
            :chain="account.chain"
          />
          <RuiTooltip v-else :popper="{ placement: 'top' }" open-delay="400">
            <template #activator>
              <RuiIcon name="links-line" />
            </template>
            <span>{{ t('common.multi_chain') }}</span>
          </RuiTooltip>
        </VAvatar>
      </div>

      <EnsAvatar :address="address" avatar class="mr-2" />

      <div :class="{ blur: !shouldShowAmount }" class="text-no-wrap">
        <div v-if="aliasName">{{ aliasName }}</div>
        <div v-else>
          {{ truncate ? truncateAddress(address, 6) : address }}
        </div>
      </div>
    </template>
    {{ account.address }}
  </RuiTooltip>
</template>
