<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';
import AddressInteractionHints from './AddressInteractionHints.vue';
import AddressInteractionLayout from './AddressInteractionLayout.vue';
import AddressInteractionToolbar from './AddressInteractionToolbar.vue';

/**
 * The address interactions card as tiers without graphs see it: the real frame, filters and hints
 * around a static sketch of a graph, with the upgrade prompt on top. Nothing here reads the user's
 * data, and the filters are inert.
 */

interface SketchNode {
  x: number;
  y: number;
  r: number;
}

interface SketchEdge {
  from: number;
  to: number;
  tone: string;
}

const SAMPLE_CHAINS: readonly string[] = [Blockchain.ETH, Blockchain.OPTIMISM, Blockchain.ARBITRUM_ONE, Blockchain.BASE, Blockchain.GNOSIS];

const NODES: readonly SketchNode[] = [
  { r: 16, x: 250, y: 260 },
  { r: 9, x: 150, y: 170 },
  { r: 9, x: 130, y: 320 },
  { r: 10, x: 230, y: 410 },
  { r: 9, x: 340, y: 160 },
  { r: 11, x: 360, y: 330 },
  { r: 12, x: 480, y: 250 },
  { r: 16, x: 710, y: 250 },
  { r: 10, x: 610, y: 140 },
  { r: 9, x: 820, y: 150 },
  { r: 10, x: 850, y: 290 },
  { r: 9, x: 770, y: 400 },
  { r: 11, x: 620, y: 370 },
  { r: 8, x: 470, y: 450 },
  { r: 8, x: 560, y: 480 },
];

const EDGES: readonly SketchEdge[] = [
  { from: 0, to: 1, tone: 'text-rui-primary' },
  { from: 0, to: 2, tone: 'text-rui-primary' },
  { from: 0, to: 3, tone: 'text-rui-info' },
  { from: 0, to: 4, tone: 'text-rui-primary' },
  { from: 0, to: 5, tone: 'text-rui-text-secondary' },
  { from: 1, to: 4, tone: 'text-rui-info' },
  { from: 2, to: 3, tone: 'text-rui-primary' },
  { from: 5, to: 6, tone: 'text-rui-success' },
  { from: 6, to: 8, tone: 'text-rui-success' },
  { from: 6, to: 12, tone: 'text-rui-text-secondary' },
  { from: 7, to: 8, tone: 'text-rui-primary' },
  { from: 7, to: 9, tone: 'text-rui-info' },
  { from: 7, to: 10, tone: 'text-rui-primary' },
  { from: 7, to: 11, tone: 'text-rui-text-secondary' },
  { from: 7, to: 12, tone: 'text-rui-primary' },
  { from: 9, to: 10, tone: 'text-rui-info' },
  { from: 13, to: 14, tone: 'text-rui-success' },
];

/** Gives the inert slider a range, so the filters row looks as it does with data. */
const SAMPLE_MAX_TRANSACTIONS = 20;
const SKELETON_CLUSTERS = 3;
const SKELETON_CONNECTIONS = 8;

const { t } = useI18n({ useScope: 'global' });
const { minimumTier } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
</script>

<template>
  <AddressInteractionLayout data-testid="address-interactions-placeholder">
    <template #header>
      <AddressInteractionToolbar
        address=""
        chain=""
        :min-transactions="1"
        :address-options="[]"
        :chains="SAMPLE_CHAINS"
        :max-transactions="SAMPLE_MAX_TRANSACTIONS"
        inert
      />
    </template>
    <div class="flex min-h-0 flex-1 flex-col bg-rui-grey-50 dark:bg-rui-grey-900">
      <div class="flex shrink-0 items-center gap-3 border-b border-default px-4 py-2.5">
        <RuiSkeletonLoader
          v-for="width in ['w-20', 'w-16', 'w-24', 'w-16']"
          :key="width"
          :class="width"
        />
      </div>
      <svg
        class="h-[60dvh] min-h-96 w-full opacity-50 xl:h-auto xl:min-h-0 xl:flex-1"
        viewBox="0 0 960 540"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <line
          v-for="edge in EDGES"
          :key="`${edge.from}-${edge.to}`"
          :class="edge.tone"
          :x1="NODES[edge.from].x"
          :y1="NODES[edge.from].y"
          :x2="NODES[edge.to].x"
          :y2="NODES[edge.to].y"
          stroke="currentColor"
          stroke-width="3"
        />
        <circle
          v-for="(node, index) in NODES"
          :key="index"
          class="text-rui-text-secondary"
          :cx="node.x"
          :cy="node.y"
          :r="node.r"
          fill="currentColor"
        />
      </svg>
    </div>
    <div class="absolute inset-0 flex items-center justify-center p-4">
      <div class="max-w-lg rounded-xl border border-default bg-rui-surface px-6 py-6 shadow-lg">
        <GetPremiumPlaceholder
          :title="t('address_interactions.premium.title')"
          :description="t('address_interactions.premium.description')"
          :minimum-tier="minimumTier"
        />
      </div>
    </div>
    <template #footer>
      <AddressInteractionHints />
    </template>
    <template #panel>
      <div
        class="flex flex-col gap-4 p-4"
        aria-hidden="true"
      >
        <RuiSkeletonLoader class="w-24" />
        <div
          v-for="cluster in SKELETON_CLUSTERS"
          :key="`cluster-${cluster}`"
          class="flex flex-col gap-2 rounded-lg border border-default p-3"
        >
          <RuiSkeletonLoader class="w-32" />
          <RuiSkeletonLoader class="w-48" />
        </div>
        <RuiSkeletonLoader class="mt-2 w-28" />
        <div
          v-for="connection in SKELETON_CONNECTIONS"
          :key="`connection-${connection}`"
          class="flex items-center gap-3"
        >
          <div class="flex shrink-0">
            <div class="size-5 rounded-full bg-rui-grey-200 dark:bg-rui-grey-700" />
            <div class="-ml-2 size-5 rounded-full bg-rui-grey-300 ring-2 ring-rui-surface dark:bg-rui-grey-600" />
          </div>
          <div class="flex flex-1 flex-col gap-1.5">
            <RuiSkeletonLoader class="w-40" />
            <RuiSkeletonLoader class="w-20" />
          </div>
        </div>
      </div>
    </template>
  </AddressInteractionLayout>
</template>
