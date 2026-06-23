<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { SnapshotChange } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { createReusableTemplate, useVirtualList } from '@vueuse/core';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isNft } from '@/modules/assets/nft-utils';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';

const { changes } = defineProps<{
  /** The ordered structural diff between the saved snapshot and the draft. */
  changes: SnapshotChange[];
  /** Snapshot timestamp (seconds) for historic FX display. */
  timestamp: number;
}>();

const { t } = useI18n({ useScope: 'global' });

interface ChangeItem {
  icon: string;
  color: string;
  label: string;
  /** Present for balance rows. */
  asset?: string;
  /** Present for location rows. */
  location?: string;
  /** Present only for the net-worth (total) change. */
  before?: BigNumber;
  after?: BigNumber;
}

/** Row height in px — also the virtual-list item height, so it must be exact. */
const ITEM_HEIGHT = 52;
/** Below this many rows we render them all (keeps column alignment + cheap); above
 * it we virtualise so a bulk edit can't mount thousands of nodes and lag the UI. */
const STATIC_LIMIT = 100;

const ADDED = { color: 'text-rui-success', icon: 'lu-plus' };
const REMOVED = { color: 'text-rui-error', icon: 'lu-minus' };
const CHANGED = { color: 'text-rui-warning', icon: 'lu-pencil' };

const [DefineRow, ReuseRow] = createReusableTemplate<{ item: ChangeItem }>();

function describe(change: SnapshotChange): ChangeItem {
  switch (change.kind) {
    case 'balance-added':
      return { ...ADDED, asset: change.after.assetIdentifier, label: t('dashboard.snapshot.detail.changes.added') };
    case 'balance-removed':
      return { ...REMOVED, asset: change.before.assetIdentifier, label: t('dashboard.snapshot.detail.changes.removed') };
    case 'balance-changed':
      return { ...CHANGED, asset: change.after.assetIdentifier, label: t('dashboard.snapshot.detail.changes.changed') };
    case 'location-added':
      return { ...ADDED, label: t('dashboard.snapshot.detail.changes.added'), location: change.location };
    case 'location-removed':
      return { ...REMOVED, label: t('dashboard.snapshot.detail.changes.removed'), location: change.location };
    case 'location-changed':
      return { ...CHANGED, label: t('dashboard.snapshot.detail.changes.changed'), location: change.location };
    case 'total-changed':
      return { ...CHANGED, after: change.after, before: change.before, label: t('dashboard.snapshot.detail.changes.net_worth') };
  }
}

const items = computed<ChangeItem[]>(() => changes.map(describe));
const virtualized = computed<boolean>(() => get(items).length > STATIC_LIMIT);

const { containerProps, list, wrapperProps } = useVirtualList(items, { itemHeight: ITEM_HEIGHT });
</script>

<template>
  <!-- Shared row so the static and virtualised paths render identically. The fixed
    verb column aligns the entities across rows without a grid. -->
  <DefineRow #default="{ item }">
    <div
      class="flex items-center gap-3 text-body-2"
      :style="{ height: `${ITEM_HEIGHT}px` }"
    >
      <div class="flex items-center gap-1.5 text-rui-text-secondary whitespace-nowrap w-28 shrink-0">
        <RuiIcon
          :name="item.icon"
          :class="item.color"
          size="16"
        />
        <span>{{ item.label }}</span>
      </div>

      <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5 min-w-0 leading-tight">
        <AssetDetails
          v-if="item.asset && !isNft(item.asset)"
          :asset="item.asset"
          :enable-association="false"
          size="26px"
        />
        <span v-else-if="item.asset">{{ item.asset }}</span>

        <LocationDisplay
          v-else-if="item.location"
          :opens-details="false"
          :identifier="item.location"
        />

        <template v-else-if="item.before && item.after">
          <SnapshotFiatDisplay
            class="text-rui-text-secondary line-through"
            :value="item.before"
            :timestamp="timestamp"
          />
          <RuiIcon
            name="lu-arrow-right"
            size="14"
            class="text-rui-text-secondary shrink-0"
          />
          <SnapshotFiatDisplay
            class="font-medium"
            :value="item.after"
            :timestamp="timestamp"
          />
        </template>
      </div>
    </div>
  </DefineRow>

  <div
    v-if="items.length === 0"
    class="text-body-2 text-rui-text-secondary"
    data-testid="snapshot-changes-empty"
  >
    {{ t('dashboard.snapshot.detail.changes.empty') }}
  </div>

  <ul
    v-else-if="!virtualized"
    class="flex flex-col"
    data-testid="snapshot-changes-list"
  >
    <li
      v-for="(item, index) in items"
      :key="index"
    >
      <ReuseRow :item="item" />
    </li>
  </ul>

  <div
    v-else
    v-bind="containerProps"
    class="max-h-[20rem]"
    data-testid="snapshot-changes-list"
  >
    <div v-bind="wrapperProps">
      <ReuseRow
        v-for="{ data, index } in list"
        :key="index"
        :item="data"
      />
    </div>
  </div>
</template>
