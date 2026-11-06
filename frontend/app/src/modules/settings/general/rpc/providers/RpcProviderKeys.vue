<script setup lang="ts">
import type { RpcProviderUsage } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useRpcProviderRemoval } from '@/modules/settings/general/rpc/providers/use-rpc-provider-removal';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

/** A removal that left some of a provider's nodes behind, named under the chips. */
interface PartialRemoval {
  usage: RpcProviderUsage;
  title: string;
  failure: string;
}

/** The chains that hold a node list, which is where a provider's nodes can be. */
const { chains } = defineProps<{
  chains: string[];
}>();

const emit = defineEmits<{
  removed: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const partialRemoval = shallowRef<PartialRemoval>();

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

/**
 * Removes every node of a provider the user already confirmed, and keeps any it could not remove.
 *
 * @remarks
 * Clears the last partial removal first, so the strip only ever describes the latest attempt.
 */
async function remove(usage: RpcProviderUsage): Promise<void> {
  set(partialRemoval, undefined);
  const title = t('rpc_provider_setup.remove.title', { provider: labelFor(usage) });
  const { failed, removed } = await removeAll(usage);
  await reload();
  emit('removed');

  if (failed > 0) {
    set(partialRemoval, {
      failure: t('rpc_provider_setup.remove.partial', { failed, provider: usage.name, removed }),
      title,
      usage,
    });
  }
}

/**
 * Retries a partial removal on the nodes the provider still holds.
 *
 * @remarks
 * The usage the strip kept predates the reload, so it still lists nodes that are gone; the retry
 * looks the provider up again instead. When nothing of it is left, there is nothing to retry.
 */
async function retryRemoval(): Promise<void> {
  const last = get(partialRemoval);
  if (!last)
    return;

  const current = get(usages).find(usage => usage.id === last.usage.id && usage.key === last.usage.key);
  if (current)
    await remove(current);
  else
    set(partialRemoval, undefined);
}

/**
 * Names every chain that loses a node.
 *
 * @remarks
 * Nothing records whether a node was added by the user or shipped by rotki (the Solana defaults
 * include a provider endpoint), so the question lists what will go rather than implying these are
 * all the user's own.
 */
function removalMessage(usage: RpcProviderUsage): string {
  return t('rpc_provider_setup.remove.message', {
    chains: usage.nodes.map(node => getChainName(node.chain)).join(', '),
    count: usage.nodes.length,
    provider: labelFor(usage),
  }, usage.nodes.length);
}

/**
 * Opens a chip's question from its close button.
 *
 * @remarks
 * The chip stops the close click from reaching the menu's activator wrapper, and binding the menu's
 * attrs on the whole chip would open the question from a click anywhere on it, so the close button
 * calls the menu's own click handler instead.
 */
function openQuestion(attrs: Record<string, unknown>): void {
  const open = attrs.onClick;
  if (typeof open === 'function')
    open();
}

watchImmediate(() => chains, reload);

defineExpose({ reload });
</script>

<template>
  <div
    v-if="usages.length > 0 || partialRemoval"
    class="flex flex-col gap-2"
  >
    <div
      v-if="usages.length > 0"
      class="flex flex-wrap items-center gap-2"
      data-testid="provider-keys"
    >
      <span class="text-xs text-rui-text-secondary">{{ t('rpc_provider_setup.remove.label') }}</span>
      <ConfirmPopover
        v-for="usage in usages"
        :key="`${usage.id}-${usage.key}`"
        :title="t('rpc_provider_setup.remove.title', { provider: labelFor(usage) })"
        :message="removalMessage(usage)"
        :confirm-label="t('rpc_provider_setup.remove.confirm')"
        @confirm="remove(usage)"
      >
        <template #activator="{ attrs }">
          <RuiChip
            size="sm"
            closeable
            :disabled="removing"
            :data-testid="usage.key ? `provider-key-${usage.id}-${usage.key}` : `provider-key-${usage.id}`"
            @click:close="openQuestion(attrs)"
          >
            {{ t('rpc_provider_setup.remove.chip', { count: usage.nodes.length, provider: labelFor(usage) }) }}
          </RuiChip>
        </template>
      </ConfirmPopover>
    </div>
    <FailureStrip
      v-if="partialRemoval"
      :title="partialRemoval.title"
      :failure="partialRemoval.failure"
      data-testid="provider-keys-remove-error"
      @retry="retryRemoval()"
    />
  </div>
</template>
