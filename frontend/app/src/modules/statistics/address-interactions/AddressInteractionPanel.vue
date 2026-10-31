<script setup lang="ts">
import type { AddressInteractionExplorer } from './use-address-interaction-explorer';
import { PAGE_SIZE } from './address-interaction-panel';
import AddressInteractionClusters from './AddressInteractionClusters.vue';
import AddressInteractionConnectionList from './AddressInteractionConnectionList.vue';
import AddressInteractionDetails from './AddressInteractionDetails.vue';
import AddressInteractionNodeSummary from './AddressInteractionNodeSummary.vue';
import AddressInteractionPath from './AddressInteractionPath.vue';

/**
 * Side panel that follows the graph selection: the clusters and every connection, then a selected
 * address and its connections, then a connection's transactions, or the path between two addresses.
 *
 * @remarks
 * `explorer` is the page's one explorer instance; it is never replaced, so reading its refs once in
 * setup keeps them reactive.
 */
const { explorer } = defineProps<{ explorer: AddressInteractionExplorer }>();

const { t } = useI18n({ useScope: 'global' });

const {
  activeChain,
  chains,
  clearConnection,
  clearPath,
  clearSelection,
  clusters,
  connections,
  hideNode,
  path,
  pathTarget,
  selectCluster,
  selectConnection,
  selectedClusterIndex,
  selectedConnection,
  selectedNode,
  startPath,
} = explorer;

const connectionLimit = shallowRef<number>(PAGE_SIZE);

watch(connections, () => {
  set(connectionLimit, PAGE_SIZE);
});
</script>

<template>
  <AddressInteractionPath
    v-if="selectedNode && pathTarget"
    :path="path"
    :from="selectedNode"
    :to="pathTarget"
    @back="clearPath()"
  />
  <AddressInteractionDetails
    v-else-if="selectedConnection"
    :connection="selectedConnection"
    :chains="chains"
    @back="clearConnection()"
  />
  <div
    v-else
    class="flex min-w-0 flex-col"
  >
    <AddressInteractionNodeSummary
      v-if="selectedNode"
      :node="selectedNode"
      @clear="clearSelection()"
      @find-path="startPath()"
      @hide="hideNode(selectedNode)"
    />
    <div class="flex flex-col gap-4 p-4">
      <AddressInteractionClusters
        v-if="!selectedNode && clusters.length > 0"
        :clusters="clusters"
        :selected-index="selectedClusterIndex"
        @select="selectCluster($event)"
      />
      <div class="flex flex-col gap-2">
        <div class="flex flex-col">
          <h3 class="text-sm font-semibold">
            {{ selectedNode
              ? t('address_interactions.connected_addresses', { count: connections.length })
              : t('address_interactions.connections', { count: connections.length }) }}
          </h3>
          <p class="text-xs text-rui-text-secondary">
            {{ t('address_interactions.sorted_by_activity') }}
          </p>
        </div>
        <AddressInteractionConnectionList
          v-model:limit="connectionLimit"
          :connections="connections"
          :focus-node-id="selectedNode?.id"
          :chain="activeChain"
          class="-mx-2"
          @select="selectConnection($event)"
        />
      </div>
    </div>
  </div>
</template>
