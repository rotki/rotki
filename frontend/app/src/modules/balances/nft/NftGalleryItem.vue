<script setup lang="ts">
import type { StyleValue } from 'vue';
import type { GalleryNft } from '@/modules/assets/nfts';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import { useNftDomainWhitelist } from '@/modules/balances/nft/use-nft-domain-whitelist';
import { useNftImage } from '@/modules/balances/nft/use-nft-image';
import AppImage from '@/modules/shell/components/AppImage.vue';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import IconLink from '@/modules/shell/components/IconLink.vue';

const { item } = defineProps<{
  item: GalleryNft;
}>();

const imageUrlSource = computed<string | null>(() => item.imageUrl);

const { isVideo, renderedMedia, shouldRender } = useNftImage(imageUrlSource);
const { allowDomain, domain, question } = useNftDomainWhitelist(imageUrlSource);

const name = computed(() => (item.name ? item.name : item.collection?.name));

const { t } = useI18n({ useScope: 'global' });

const mediaStyle = computed<StyleValue>(() => {
  const backgroundColor = item.backgroundColor;
  if (!get(shouldRender) || !backgroundColor)
    return {};

  return { backgroundColor };
});
</script>

<template>
  <RuiCard
    no-padding
    class="mx-auto overflow-hidden"
  >
    <div class="relative flex">
      <RuiTooltip
        :options="{ placement: 'top' }"
        :disabled="shouldRender"
        :open-delay="400"
        class="w-full"
        :class-names="{ tooltip: 'max-w-40' }"
      >
        <template #activator>
          <ExternalLink
            :url="item.externalLink"
            class="w-full"
            custom
          >
            <video
              v-if="isVideo"
              controls
              width="auto"
              :src="renderedMedia"
              :style="mediaStyle"
              class="w-full max-w-full h-auto object-contain aspect-square"
            />
            <AppImage
              v-else
              :src="renderedMedia"
              fit="contain"
              :style="mediaStyle"
              width="100%"
              class="object-contain aspect-square"
            />
          </ExternalLink>
        </template>

        {{ t('nft_balance_table.hidden_hint') }}
      </RuiTooltip>

      <ConfirmPopover
        v-if="!shouldRender"
        class="absolute right-2 bottom-2"
        tone="warning"
        :title="question.title"
        :message="question.message"
        :confirm-label="question.confirmLabel"
        @confirm="allowDomain()"
      >
        <template #activator="{ attrs }">
          <RuiTooltip
            :options="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                class="p-2!"
                icon
                data-testid="nft-allow-domain"
                v-bind="attrs"
              >
                <RuiIcon
                  name="lu-lock-keyhole-open"
                  size="16"
                />
              </RuiButton>
            </template>
            {{ t('nft_gallery.allow_domain') }}
            <strong class="text-rui-warning-lighter">{{ domain }}</strong>
          </RuiTooltip>
        </template>
      </ConfirmPopover>
    </div>
    <div class="p-4 flex flex-col min-w-0">
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
        :class-names="{ tooltip: 'max-w-80' }"
        class="block truncate text-body-1 font-medium"
      >
        <template #activator>
          {{ name }}
        </template>
        {{ name }}
      </RuiTooltip>
      <RuiTooltip
        v-if="item.collection"
        :options="{ placement: 'top' }"
        :open-delay="400"
        :disabled="!item.collection.description"
        :class-names="{ tooltip: 'max-w-80' }"
        class="block truncate text-body-2 text-rui-text-secondary"
      >
        <template #activator>
          {{ item.collection.name }}
        </template>
        {{ item.collection.description }}
      </RuiTooltip>
      <div class="mt-4 flex items-end justify-between gap-2">
        <div class="flex flex-col min-w-0">
          <AssetAmountDisplay
            class="font-medium"
            :amount="item.priceInAsset"
            :asset="item.priceAsset"
          />
          <FiatDisplay
            class="text-body-2 text-rui-text-secondary"
            :value="item.price"
            no-scramble
            symbol="ticker"
          />
        </div>
        <IconLink
          v-if="item.permalink"
          :url="item.permalink"
          class="-mr-1.5 -mb-0.5 shrink-0"
        />
      </div>
    </div>
  </RuiCard>
</template>
