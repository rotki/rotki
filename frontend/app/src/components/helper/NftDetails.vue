<script setup lang="ts">
import type { StyleValue } from 'vue';
import AppImage from '@/components/common/AppImage.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useNftImage } from '@/composables/nft-image';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useConfirmStore } from '@/store/confirm';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { uniqueStrings } from '@/utils/data';
import { getDomain } from '@/utils/url';

const props = withDefaults(
  defineProps<{
    identifier: string;
    styled?: StyleValue;
    size?: string;
  }>(),
  {
    size: '50px',
    styled: undefined,
  },
);

const { identifier } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const frontendStore = useFrontendSettingsStore();

const { whitelistedDomainsForNftImages } = storeToRefs(frontendStore);
const { updateSetting } = frontendStore;

const balanceData = assetInfo(identifier);

const { t } = useI18n({ useScope: 'global' });

const imageUrlSource = computed<string | null>(() => get(balanceData)?.imageUrl || null);

const { isVideo, renderedMedia, shouldRender } = useNftImage(imageUrlSource);

const domain = computed<string | null>(() => getDomain(get(imageUrlSource) || ''));

const { show } = useConfirmStore();

function showAllowDomainConfirmation() {
  show(
    {
      message: t(
        'general_settings.nft_setting.update_whitelist_confirmation.message',
        {
          domain: get(domain),
        },
        2,
      ),
      title: t('general_settings.nft_setting.update_whitelist_confirmation.title'),
    },
    allowDomain,
  );
}

function allowDomain() {
  const domainVal = get(domain);

  if (!domainVal)
    return;

  const newWhitelisted = [...get(whitelistedDomainsForNftImages), domainVal].filter(uniqueStrings);

  updateSetting({ whitelistedDomainsForNftImages: newWhitelisted });
}

const collectionName = computed<string | null>(() => {
  const data = get(balanceData);
  if (!data || !data.collectionName)
    return null;

  const tokenId = get(identifier).split('_')[3];
  return `${data.collectionName} #${tokenId}`;
});

const name = computed<string | null>(() => {
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
    tokenId: data[3],
  };
});
</script>

<template>
  <div>
    <div class="flex items-center overflow-hidden">
      <div class="cursor-pointer">
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :disabled="shouldRender"
          :open-delay="400"
          class="w-full"
          tooltip-class="max-w-[10rem]"
        >
          <template #activator>
            <div
              class="my-2 bg-rui-grey-200 rounded flex items-center justify-center"
              :style="[styled, { width: size, height: size, maxWidth: size, minWidth: size }]"
              @click="!shouldRender ? showAllowDomainConfirmation() : null"
            >
              <video
                v-if="isVideo"
                width="100%"
                height="100%"
                :src="renderedMedia"
              />
              <AppImage
                v-else
                class="rounded overflow-hidden"
                :src="renderedMedia"
                :size="size"
                contain
              />
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
        <div
          v-else-if="name"
          class="flex-1 max-w-[400px]"
        >
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
          <div class="flex items-center">
            <div>{{ t('nft_balance_table.contract_address') }}:</div>
            <div class="pl-1 font-medium">
              <HashLink
                :text="fallbackData.address"
                location="eth"
              />
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
