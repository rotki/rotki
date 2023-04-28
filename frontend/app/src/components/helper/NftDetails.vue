<script setup lang="ts">
import { type ComputedRef } from 'vue';
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
const { shouldRenderImage } = useNfts();

const frontendStore = useFrontendSettingsStore();

const { whitelistedDomainsForNftImages } = storeToRefs(frontendStore);
const { updateSetting } = frontendStore;

const balanceData = assetInfo(identifier);

const { tc } = useI18n();

const imageUrlSource: ComputedRef<string | null> = computed(
  () => get(balanceData)?.imageUrl || null
);

const domain: ComputedRef<string | null> = computed(() =>
  getDomain(get(imageUrlSource) || '')
);

const { show } = useConfirmStore();

const showAllowDomainConfirmation = () => {
  show(
    {
      title: tc(
        'general_settings.nft_setting.update_whitelist_confirmation.title'
      ),
      message: tc(
        'general_settings.nft_setting.update_whitelist_confirmation.message',
        2,
        {
          domain: get(domain)
        }
      )
    },
    allowDomain
  );
};

const allowDomain = () => {
  const domainVal = get(domain);

  if (!domainVal) {
    return;
  }

  const newWhitelisted = [
    ...get(whitelistedDomainsForNftImages),
    domainVal
  ].filter(uniqueStrings);

  updateSetting({ whitelistedDomainsForNftImages: newWhitelisted });
};

const renderImage: ComputedRef<boolean> = computed(() => {
  const image = get(imageUrlSource);

  if (!image) {
    return true;
  }

  return shouldRenderImage(image);
});

const imageUrl: ComputedRef<string> = computed(() => {
  const image = get(imageUrlSource);

  if (!image || !get(renderImage)) {
    return './assets/images/placeholder.svg';
  }

  return image;
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

const { isPending } = useAssetCacheStore();
const isNftDetailLoading = isPending(identifier);

const fallbackData = computed(() => {
  const id = get(identifier);

  const data = id.split('_');
  return {
    address: data[2],
    tokenId: data[3]
  };
});
</script>

<template>
  <div>
    <div class="d-flex align-center overflow-hidden">
      <div :class="css.wrapper">
        <v-tooltip
          top
          :disabled="renderImage"
          max-width="200"
          open-delay="200"
          class="mdi-cursor-pointer"
        >
          <template #activator="{ on }">
            <div
              class="my-2"
              :class="css.preview"
              :style="styled"
              v-on="on"
              @click="!renderImage ? showAllowDomainConfirmation() : null"
            >
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
          </template>

          <span>
            {{ tc('nft_balance_table.hidden_hint') }}
            {{ tc('nft_gallery.allow_domain') }}
            <span class="font-weight-bold warning--text">{{ domain }}</span>
          </span>
        </v-tooltip>
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
            <div>{{ tc('nft_balance_table.contract_address') }}:</div>
            <div class="pl-1 font-weight-medium">
              <hash-link :text="fallbackData.address" />
            </div>
          </div>
          <div class="d-flex">
            <div>{{ tc('nft_balance_table.token_id') }}:</div>
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

.wrapper {
  cursor: pointer;
}
</style>
