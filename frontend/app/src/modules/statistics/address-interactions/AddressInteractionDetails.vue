<script setup lang="ts">
import type { InteractionConnection } from './address-interaction-graph';
import HashLink from '@/modules/shell/components/HashLink.vue';
import AddressInteractionChainActivity from './AddressInteractionChainActivity.vue';
import { useChainColors } from './use-chain-colors';

/**
 * One address pair: both addresses, then the transactions they share, grouped by chain.
 *
 * @remarks
 * The addresses link to the explorer of the first chain the pair shares, since both addresses are
 * known to exist there.
 */
const { connection, chains } = defineProps<{
  connection: InteractionConnection;
  /** Every chain in the data, so each chain keeps the colour it has on the graph. */
  chains: readonly string[];
}>();

const emit = defineEmits<{
  back: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const explorerChain = computed<string | undefined>(() => connection.activity[0]?.chain);

const { chainColor } = useChainColors(() => chains);

interface ChainShare {
  chain: string;
  color: string;
  /** Share of the pair's transactions, in percent. */
  percent: number;
}

const shares = computed<ChainShare[]>(() => connection.activity.map(({ chain, txHashes }) => ({
  chain,
  color: chainColor(chain),
  percent: txHashes.length / Math.max(1, connection.txCount) * 100,
})));
</script>

<template>
  <div
    class="flex min-w-0 flex-col"
    data-testid="interaction-details"
  >
    <div class="flex flex-col gap-3 border-b border-default p-4 pt-2">
      <RuiButton
        variant="text"
        size="sm"
        class="-ml-2 self-start"
        data-testid="interaction-details-back"
        @click="emit('back')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-arrow-left"
            size="14"
          />
        </template>
        {{ t('common.actions.back') }}
      </RuiButton>
      <h3
        class="text-base font-semibold"
        aria-live="polite"
      >
        {{ t('address_interactions.selected_connection') }}
      </h3>
      <div class="flex flex-col">
        <HashLink
          :text="connection.source.address"
          :location="explorerChain"
          :size="14"
        />
        <div class="flex items-center gap-2 py-1 pl-1 text-xs text-rui-text-secondary">
          <RuiIcon
            name="lu-arrow-up-down"
            size="14"
            aria-hidden="true"
          />
          {{ t('address_interactions.transactions', { count: connection.txCount }) }}
        </div>
        <HashLink
          :text="connection.target.address"
          :location="explorerChain"
          :size="14"
        />
      </div>
      <div
        class="flex h-1.5 w-full gap-0.5 overflow-hidden rounded-full"
        aria-hidden="true"
        data-testid="interaction-chain-split"
      >
        <span
          v-for="share in shares"
          :key="share.chain"
          class="h-full"
          :style="{ backgroundColor: share.color, width: `${share.percent}%` }"
        />
      </div>
    </div>
    <div class="flex min-w-0 flex-col gap-5 p-4">
      <AddressInteractionChainActivity
        v-for="activity in connection.activity"
        :key="`${connection.id}:${activity.chain}`"
        :activity="activity"
        :color="chainColor(activity.chain)"
      />
    </div>
  </div>
</template>
