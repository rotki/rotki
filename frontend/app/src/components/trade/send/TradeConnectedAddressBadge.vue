<script setup lang="ts">
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useWalletHelper } from '@/composables/trade/wallet-helper';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletStore } from '@/store/trade/wallet';

defineProps<{
  appBar?: boolean;
}>();

const { t } = useI18n();

const walletStore = useWalletStore();
const { connected, connectedAddress, connectedChainId } = storeToRefs(walletStore);
const { disconnect, open } = walletStore;

const { getChainFromChainId } = useWalletHelper();

const chain = computed(() => {
  const chainId = get(connectedChainId);
  if (!chainId) {
    return undefined;
  }
  return getChainFromChainId(chainId);
});
</script>

<template>
  <RuiButton
    v-if="!connected && !appBar"
    color="primary"
    class="!py-2"
    @click="open()"
  >
    <template #prepend>
      <RuiIcon
        name="lu-wallet"
        size="18"
      />
    </template>
    {{ t('trade.actions.connect_wallet') }}
  </RuiButton>

  <RuiMenu
    v-else-if="connectedAddress"
    full-width
    class="flex"
  >
    <template #activator="{ attrs }">
      <div
        v-bind="attrs"
        class="border border-default rounded-md px-2 py-1 flex items-center gap-2 font-mono text-sm font-medium cursor-pointer"
      >
        <div class="p-0.5 rounded-full size-3 border border-rui-success-lighter/40">
          <div class="size-full rounded-full bg-rui-success-lighter" />
        </div>
        <ChainIcon
          v-if="chain"
          :chain="chain"
          size="14px"
        />
        <HashLink
          class="!pl-0"
          :text="connectedAddress"
          copy-only
        />
      </div>
    </template>
    <template #default="{ width }">
      <div
        class="py-1"
        :style="{ width: `${width}px` }"
      >
        <RuiButton
          variant="list"
          size="sm"
          @click="open()"
        >
          {{ t('trade.actions.open_wallet') }}
        </RuiButton>
        <RuiButton
          variant="list"
          size="sm"
          @click="disconnect()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-log-out"
              size="14"
            />
          </template>
          {{ t('trade.actions.disconnect') }}
        </RuiButton>
      </div>
    </template>
  </RuiMenu>
</template>
