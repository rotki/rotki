<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { type AssetInfoWithId, Zero } from '@rotki/common';
import { useTemplateRef } from 'vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import AssetDetailsMenuContent from '@/components/helper/AssetDetailsMenuContent.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useRefMap } from '@/composables/utils/useRefMap';
import { AssetAmountDisplay, AssetValueDisplay } from '@/modules/amount-display/components';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { event } = toRefs(props);
const { assetSymbol, assetInfo } = useAssetInfoRetrieval();

const showBalance = computed<boolean>(() => get(event).eventType !== 'informational');

const eventAsset = useRefMap(event, ({ asset }) => asset);

const symbol = assetSymbol(eventAsset, {
  collectionParent: false,
});

const menuOpened = ref<boolean>(false);
const menuContentRef = useTemplateRef<InstanceType<typeof AssetDetailsMenuContent>>('menuContentRef');

const ASSET_RESOLUTION_OPTIONS: AssetResolutionOptions = { collectionParent: false };
const assetDetails = assetInfo(eventAsset, ASSET_RESOLUTION_OPTIONS);

const currentAsset = computed<AssetInfoWithId>(() => ({
  ...get(assetDetails),
  identifier: get(eventAsset),
}));

watch(menuOpened, (menuOpened) => {
  if (!menuOpened) {
    get(menuContentRef)?.setConfirm(false);
  }
});

function openMenuHandler(event: MouseEvent): void {
  event.preventDefault();
  event.stopPropagation();
  set(menuOpened, !get(menuOpened));
}
</script>

<template>
  <!-- Disable scroll/resize listeners to optimize performance in virtualized lists -->
  <RuiMenu
    v-model="menuOpened"
    class="flex"
    menu-class="w-[16rem] max-w-[90%] z-[100]"
    :popper="{ placement: 'bottom-start', scroll: false, resize: false }"
  >
    <template #activator="{ attrs }">
      <div
        class="py-2 flex items-center gap-2 overflow-hidden cursor-pointer hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800 rounded-md group/asset -ml-1 pl-1 min-h-14 pr-14 relative"
        v-bind="attrs"
        @contextmenu="openMenuHandler($event)"
      >
        <AssetDetails
          size="32px"
          icon-only
          hide-menuca
          optimize-for-virtual-scroll
          :asset="event.asset"
          :resolution-options="ASSET_RESOLUTION_OPTIONS"
          @refresh="emit('refresh')"
        />
        <div
          v-if="showBalance"
          class="flex flex-col min-w-0"
        >
          <AssetAmountDisplay
            :amount="event.amount"
            :asset="event.asset"
            no-collection-parent
            class="text-sm"
          />
          <AssetValueDisplay
            :key="event.timestamp"
            :amount="event.amount"
            :asset="event.asset"
            :value="Zero"
            :timestamp="{ ms: event.timestamp }"
            class="text-rui-text-secondary text-[13px]"
          />
        </div>
        <div
          v-else
          class="text-truncate text-sm"
        >
          {{ symbol }}
        </div>

        <div class="bg-gradient-to-r from-transparent to-white dark:to-rui-grey-900 -my-2 pr-2 h-[calc(100%+1rem)] flex items-center opacity-0 group-hover/asset:opacity-100 z-[1] absolute right-0">
          <RuiButton
            variant="text"
            icon
            class="!p-2"
            @click.stop="openMenuHandler($event)"
          >
            <RuiIcon
              name="lu-ellipsis-vertical"
              size="20"
            />
          </RuiButton>
        </div>
      </div>
    </template>

    <AssetDetailsMenuContent
      ref="menuContentRef"
      :asset="currentAsset"
      icon-only
      :hide-actions="false"
      :is-collection-parent="false"
      @refresh="emit('refresh')"
    />
  </RuiMenu>
</template>
