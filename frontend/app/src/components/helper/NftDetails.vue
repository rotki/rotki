<template>
  <div>
    <div class="d-flex align-center" :class="css.wrapper">
      <div class="my-2" :class="css.preview" :style="styled">
        <template v-if="imageUrl">
          <video
            v-if="isVideo(imageUrl)"
            width="100%"
            height="100%"
            aspect-ratio="1"
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
      <div class="ml-5">
        <v-skeleton-loader
          v-if="loading"
          class="mt-1"
          width="100"
          type="text"
        />
        <div v-else-if="name" class="font-weight-medium" :class="css.name">
          {{ name }}
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
<script setup lang="ts">
import { useSectionLoading } from '@/composables/common';
import { NftAsset, useNftAssetInfoStore } from '@/store/assets/nft';
import { Section } from '@/types/status';
import { isVideo } from '@/utils/nft';

const props = defineProps({
  identifier: {
    required: true,
    type: String
  },
  styled: { required: false, type: Object, default: () => null }
});

const css = useCssModule();

const { identifier } = toRefs(props);
const { getNftDetails } = useNftAssetInfoStore();

const balanceData = getNftDetails(identifier);

const imageUrl = computed<string | null>(() => {
  return get(balanceData)?.imageUrl ?? '/assets/images/placeholder.svg';
});

const getCollectionName = (data: NftAsset | null): string | null => {
  if (!data || !data.collectionName) {
    return null;
  }
  const tokenId = data.identifier.split('_')[3];
  return `${data.collectionName} #${tokenId}`;
};

const name = computed<string | null>(() => {
  const data = get(balanceData);
  return data?.name || getCollectionName(data) || null;
});

const { shouldShowLoadingScreen: isLoading } = useSectionLoading();
const loading = isLoading(Section.NON_FUNGIBLE_BALANCES);

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

<style module lang="scss">
.wrapper {
  overflow: hidden;
}

.preview {
  background: #f5f5f5;
  width: 50px;
  height: 50px;
  max-width: 50px;
  min-width: 50px;
}

.name {
  flex: 1;
}
</style>
