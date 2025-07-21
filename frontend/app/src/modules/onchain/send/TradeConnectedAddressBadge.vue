<script setup lang="ts">
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useInterop } from '@/composables/electron-interop';
import { useWalletBridge } from '@/composables/wallet-bridge';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';

defineProps<{
  appBar?: boolean;
  showWalletBridge?: boolean;
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const walletStore = useWalletStore();
const { connected, connectedAddress, connectedChainId } = storeToRefs(walletStore);
const { disconnect, open } = walletStore;

const { getChainFromChainId } = useWalletHelper();
const { isPackaged } = useInterop();
const { openWalletBridge } = useWalletBridge();

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
    :loading="loading"
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
    close-on-content-click
    class="flex min-h-9"
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
          :location="chain"
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
          v-if="isPackaged"
          variant="list"
          size="sm"
          @click="openWalletBridge()"
        >
          {{ t('trade.bridge.connect_browser_wallet') }}
          <template #append>
            <RuiIcon
              name="lu-arrow-up-right"
              size="18"
            />
          </template>
        </RuiButton>
        <RuiButton
          variant="list"
          size="sm"
          @click="disconnect()"
        >
          <template #append>
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
