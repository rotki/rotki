<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type StyleValue } from 'vue/types/jsx';
import { isVideo } from '@/utils/nft';

const props = withDefaults(
  defineProps<{
    identifier: string;
    styled?: StyleValue;
    size?: string;
  }>(),
  {
    styled: undefined,
    size: '50px'
  }
);

const css = useCssModule();

const { identifier } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();
const { shouldRenderImage } = useNfts();

const frontendStore = useFrontendSettingsStore();

const { whitelistedDomainsForNftImages } = storeToRefs(frontendStore);
const { updateSetting } = frontendStore;

const balanceData = assetInfo(identifier);

const { t } = useI18n();

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
      title: t(
        'general_settings.nft_setting.update_whitelist_confirmation.title'
      ),
      message: t(
        'general_settings.nft_setting.update_whitelist_confirmation.message',
        {
          domain: get(domain)
        },
        2
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
    <div class="flex items-center overflow-hidden">
      <div class="cursor-pointer">
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :disabled="renderImage"
          :open-delay="400"
          class="w-full"
          tooltip-class="max-w-[10rem]"
        >
          <template #activator>
            <div
              class="my-2 bg-rui-grey-200 rounded flex items-center justify-center"
              :class="css.preview"
              :style="styled"
              @click="!renderImage ? showAllowDomainConfirmation() : null"
            >
              <template v-if="imageUrl">
                <video
                  v-if="isVideo(imageUrl)"
                  width="100%"
                  height="100%"
                  :src="imageUrl"
                />
                <AppImage
                  v-else
                  class="rounded overflow-hidden"
                  :src="imageUrl"
                  :size="size"
                  contain
                />
              </template>
            </div>
          </template>

          {{ t('nft_balance_table.hidden_hint') }}
          {{ t('nft_gallery.allow_domain') }}
          <strong class="text-rui-warning-lighter">
            {{ domain }}
          </strong>
        </RuiTooltip>
      </div>

      <div class="ml-3 overflow-hidden flex-fill">
        <template v-if="isNftDetailLoading">
          <RuiSkeletonLoader class="mt-1 mb-1.5 w-[7.5rem]" />
          <RuiSkeletonLoader class="mt-1 w-[5rem]" />
        </template>
        <div v-else-if="name" :class="css['nft-details']">
          <div class="font-medium text-truncate">
            {{ name }}
          </div>
          <div
            v-if="collectionName"
            class="text-rui-text-secondary text-truncate"
          >
            {{ collectionName }}
          </div>
        </div>
        <div v-else>
          <div class="flex">
            <div>{{ t('nft_balance_table.contract_address') }}:</div>
            <div class="pl-1 font-medium">
              <HashLink :text="fallbackData.address" />
            </div>
          </div>
          <div class="flex">
            <div>{{ t('nft_balance_table.token_id') }}:</div>
            <div class="pl-1 font-medium">
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
  width: v-bind(size);
  height: v-bind(size);
  max-width: v-bind(size);
  min-width: v-bind(size);
}

.nft-details {
  flex: 1;
  max-width: 400px;
}
</style>
