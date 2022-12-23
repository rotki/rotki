<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { Section } from '@/types/status';
import { isVideo } from '@/utils/nft';

const props = defineProps({
  identifier: {
    required: true,
    type: String
  },
  styled: { required: false, type: Object, default: () => null },
  size: { required: false, type: String, default: '50px' }
});

const css = useCssModule();

const { identifier } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const balanceData = assetInfo(identifier);

const imageUrl = computed<string | null>(() => {
  return get(balanceData)?.imageUrl ?? './assets/images/placeholder.svg';
});

const collectionName: ComputedRef<string | null> = computed(() => {
  const data = get(balanceData);
  if (!data || !data.collectionName) {
    return null;
  }
  const tokenId = get(identifier).split('_')[3];
  return `${data.collectionName} #${tokenId}`;
});

const name: ComputedRef<string | null> = computed(() => {
  const data = get(balanceData);
  return data?.name || get(collectionName);
});

const { shouldShowLoadingScreen: isLoading } = useSectionLoading();
const loading = isLoading(Section.NON_FUNGIBLE_BALANCES);

const { isPending } = useAssetCacheStore();
const isNftDetailLoading: ComputedRef<boolean> = computed(
  () => get(loading) || get(isPending(identifier))
);

const fallbackData = computed(() => {
  const id = get(identifier);

  const data = id.split('_');
  return {
    address: data[2],
    tokenId: data[3]
  };
});

const { t } = useI18n();
</script>
<template>
  <div>
    <div class="d-flex align-center" :class="css.wrapper">
      <div class="my-2" :class="css.preview" :style="styled">
        <template v-if="imageUrl">
          <video
            v-if="isVideo(imageUrl)"
            width="100%"
            height="100%"
            :src="imageUrl"
          />
          <v-img
            v-else
            :src="imageUrl"
            width="100%"
            height="100%"
            contain
            aspect-ratio="1"
          />
        </template>
      </div>
      <div class="ml-5 overflow-hidden flex-fill">
        <template v-if="isNftDetailLoading">
          <v-skeleton-loader class="mt-1" width="120" type="text" />
          <v-skeleton-loader class="mt-1" width="80" type="text" />
        </template>
        <div v-else-if="name" :class="css['nft-details']">
          <div class="font-weight-medium" :class="css['nft-details__entry']">
            {{ name }}
          </div>
          <div
            v-if="collectionName"
            class="grey--text"
            :class="css['nft-details__entry']"
          >
            {{ collectionName }}
          </div>
        </div>
        <div v-else>
          <div class="d-flex">
            <div>{{ t('nft_balance_table.contract_address') }}:</div>
            <div class="pl-1 font-weight-medium">
              <hash-link :text="fallbackData.address" />
            </div>
          </div>
          <div class="d-flex">
            <div>{{ t('nft_balance_table.token_id') }}:</div>
            <div class="pl-1 font-weight-medium">
              {{ fallbackData.tokenId }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style module lang="scss">
.wrapper {
  overflow: hidden;
}

.preview {
  background: #f5f5f5;
  width: v-bind(size);
  height: v-bind(size);
  max-width: v-bind(size);
  min-width: v-bind(size);
}

.nft-details {
  flex: 1;
  max-width: 400px;

  &__entry {
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
  }
}
</style>
