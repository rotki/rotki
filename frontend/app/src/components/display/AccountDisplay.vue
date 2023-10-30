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
  <VTooltip top open-delay="400" :disabled="!truncate">
    <template #activator="{ on }">
      <VRow align="center" no-gutters class="flex-nowrap" v-on="on">
        <VCol v-if="!hideChainIcon" cols="auto" class="pr-2">
          <VAvatar left size="28px" class="mr-0">
            <ChainIcon
              v-if="account.chain && account.chain !== 'ALL'"
              size="24px"
              :chain="account.chain"
            />
            <VTooltip v-else top>
              <template #activator="{ childOn }">
                <VIcon v-on="childOn"> mdi-link-variant </VIcon>
              </template>
              <span>{{ t('common.multi_chain') }}</span>
            </VTooltip>
          </VAvatar>
        </VCol>

        <EnsAvatar :address="address" avatar class="mr-2" />

        <VCol
          cols="auto"
          :class="{ 'blur-content': !shouldShowAmount }"
          class="text-no-wrap"
        >
          <div v-if="aliasName">{{ aliasName }}</div>
          <div v-else>
            {{ truncate ? truncateAddress(address, 6) : address }}
          </div>
        </VCol>
      </VRow>
    </template>
    <div>
      {{ account.address }}
    </div>
  </VTooltip>
</template>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
