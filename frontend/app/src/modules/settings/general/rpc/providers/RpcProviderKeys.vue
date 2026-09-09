<script setup lang="ts">
import type { RpcProviderUsage } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useRpcProviderRemoval } from '@/modules/settings/general/rpc/providers/use-rpc-provider-removal';

/** The chains that hold a node list, which is where a provider's nodes can be. */
const { chains } = defineProps<{
  chains: string[];
}>();

const emit = defineEmits<{
  removed: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { show } = useConfirmStore();
const { setMessage } = useMessageStore();
const { getChainName } = useSupportedChains();
const { refresh, removeAll, removing, usages } = useRpcProviderRemoval();

async function reload(): Promise<void> {
  await refresh(chains);
}

/**
 * Names a provider, and its key when that is the only thing telling two entries apart.
 *
 * @remarks
 * Showing the key on every chip would be noise; showing it on none would make two keys of one
 * provider indistinguishable, which is exactly the case where removing the wrong one costs the most.
 */
function labelFor(usage: RpcProviderUsage): string {
  const shared = get(usages).filter(other => other.id === usage.id).length > 1;
  return shared && usage.key ? `${usage.name} ${usage.key}` : usage.name;
}

async function remove(usage: RpcProviderUsage): Promise<void> {
  const { failed, removed } = await removeAll(usage);
  await reload();
  emit('removed');

  if (failed > 0) {
    setMessage({
      description: t('rpc_provider_setup.remove.partial', { failed, provider: usage.name, removed }),
      success: false,
      title: t('rpc_provider_setup.remove.title', { provider: labelFor(usage) }),
    });
  }
}

/**
 * Names every chain that loses a node.
 *
 * @remarks
 * Nothing records whether a node was added by the user or shipped by rotki — the Solana defaults
 * include a provider endpoint — so the confirmation lists what will go rather than implying these
 * are all the user's own.
 */
function confirmRemoval(usage: RpcProviderUsage): void {
  show({
    message: t('rpc_provider_setup.remove.message', {
      chains: usage.nodes.map(node => getChainName(node.chain)).join(', '),
      count: usage.nodes.length,
      provider: labelFor(usage),
    }, usage.nodes.length),
    primaryAction: t('rpc_provider_setup.remove.confirm'),
    title: t('rpc_provider_setup.remove.title', { provider: labelFor(usage) }),
  }, async () => remove(usage));
}

watchImmediate(() => chains, reload);

defineExpose({ reload });
</script>

<template>
  <div
    v-if="usages.length > 0"
    class="flex flex-wrap items-center gap-2"
    data-testid="provider-keys"
  >
    <span class="text-xs text-rui-text-secondary">{{ t('rpc_provider_setup.remove.label') }}</span>
    <RuiChip
      v-for="usage in usages"
      :key="`${usage.id}-${usage.key}`"
      size="sm"
      closeable
      :disabled="removing"
      :data-testid="usage.key ? `provider-key-${usage.id}-${usage.key}` : `provider-key-${usage.id}`"
      @click:close="confirmRemoval(usage)"
    >
      {{ t('rpc_provider_setup.remove.chip', { count: usage.nodes.length, provider: labelFor(usage) }) }}
    </RuiChip>
  </div>
</template>
