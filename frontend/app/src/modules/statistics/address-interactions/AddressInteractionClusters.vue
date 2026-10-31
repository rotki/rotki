<script setup lang="ts">
import type { InteractionNode } from './address-interaction-graph';
import type { InteractionCluster } from './interaction-clusters';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import AddressInteractionAddress from './AddressInteractionAddress.vue';
import AddressInteractionPair from './AddressInteractionPair.vue';

/**
 * Groups of addresses anyone reading the chain can tie together, each with the link that holds it
 * together most loosely, so the user can see what a single transaction gave away.
 */
const { clusters, selectedIndex } = defineProps<{
  clusters: readonly InteractionCluster[];
  selectedIndex?: number;
}>();

const emit = defineEmits<{
  select: [index: number];
}>();

/** How many clusters show before the rest fold behind "Show all". */
const CLUSTER_PREVIEW = 5;

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

const expanded = ref<boolean>(false);

interface WeakestLink {
  ends: InteractionNode[];
  chains: string[];
  txCount: number;
}

interface ClusterCard {
  index: number;
  lead: InteractionNode;
  addresses: number;
  txCount: number;
  weakest?: WeakestLink;
}

const cards = computed<ClusterCard[]>(() => {
  const shown = get(expanded) ? clusters : clusters.slice(0, CLUSTER_PREVIEW);
  return shown.map((cluster, index) => {
    const link = cluster.weakestLink;
    return {
      addresses: cluster.nodeIds.length,
      index,
      lead: cluster.lead,
      txCount: cluster.txCount,
      weakest: link && { chains: link.activity.map(({ chain }) => chain), ends: [link.source, link.target], txCount: link.txCount },
    };
  });
});
</script>

<template>
  <section
    class="flex flex-col gap-2"
    data-testid="interaction-clusters"
  >
    <div class="flex flex-col">
      <h3 class="text-sm font-semibold">
        {{ t('address_interactions.cluster.heading', { count: clusters.length }) }}
      </h3>
      <p class="text-xs text-rui-text-secondary">
        {{ t('address_interactions.cluster.help') }}
      </p>
    </div>
    <ul class="flex flex-col gap-2 pl-0">
      <li
        v-for="card in cards"
        :key="card.index"
      >
        <button
          type="button"
          class="flex w-full flex-col gap-2 rounded-lg border px-3 py-2.5 text-left transition-colors hover:bg-rui-grey-50 focus-visible:outline-2 focus-visible:outline-rui-primary dark:hover:bg-rui-grey-900"
          :class="selectedIndex === card.index ? 'border-rui-primary bg-rui-primary/5' : 'border-default'"
          :aria-pressed="selectedIndex === card.index"
          data-testid="interaction-cluster"
          @click="emit('select', card.index)"
        >
          <span class="flex w-full items-center justify-between gap-2">
            <AddressInteractionAddress
              :node="card.lead"
              class="min-w-0 truncate text-sm font-medium"
            />
            <RuiChip
              size="sm"
              color="grey"
              class="shrink-0"
            >
              {{ t('address_interactions.cluster.addresses', { count: card.addresses }, card.addresses) }}
            </RuiChip>
          </span>
          <span class="-mt-1 text-xs text-rui-text-secondary">
            {{ t('address_interactions.tx_count', { count: card.txCount }, card.txCount) }}
          </span>
          <span
            class="flex w-full flex-col gap-0.5 border-t border-default pt-2 text-xs"
            data-testid="interaction-cluster-weakest"
          >
            <span class="font-medium text-rui-text-secondary">
              {{ t('address_interactions.cluster.weakest_link') }}
            </span>
            <template v-if="card.weakest">
              <AddressInteractionPair :nodes="card.weakest.ends" />
              <span class="flex items-center gap-1 text-rui-text-secondary">
                <LocationIcon
                  v-for="chain in card.weakest.chains"
                  :key="chain"
                  :item="chain"
                  :title="getChainName(chain)"
                  icon
                  size="12px"
                />
                {{ t('address_interactions.tx_count', { count: card.weakest.txCount }, card.weakest.txCount) }}
              </span>
            </template>
            <span
              v-else
              class="text-rui-text-secondary"
            >
              {{ t('address_interactions.cluster.no_weakest_link') }}
            </span>
          </span>
        </button>
      </li>
    </ul>
    <RuiButton
      v-if="clusters.length > CLUSTER_PREVIEW"
      variant="text"
      color="primary"
      size="sm"
      data-testid="interaction-clusters-toggle"
      @click="expanded = !expanded"
    >
      {{ expanded ? t('address_interactions.cluster.show_less') : t('address_interactions.cluster.show_all', { count: clusters.length }) }}
    </RuiButton>
  </section>
</template>
