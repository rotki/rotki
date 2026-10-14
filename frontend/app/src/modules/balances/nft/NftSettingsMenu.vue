<script setup lang="ts">
import { transformCase } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import QueriedAddressDialog from '@/modules/accounts/QueriedAddressDialog.vue';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { Module } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import NftImageRenderingSetting from '@/modules/settings/general/nft/NftImageRenderingSetting.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const manageAddresses = ref<boolean>(false);

const { fetchQueriedAddresses } = useQueriedAddressOperations();
const { queriedAddresses } = storeToRefs(useSessionMetadataStore());

/** With none listed every Ethereum address is queried; listing some limits the module to those. */
const queriedCount = computed<number>(() => (get(queriedAddresses)[transformCase(Module.NFTS, true)] ?? []).length);

function openAddresses(): void {
  set(open, false);
  set(manageAddresses, true);
}

onMounted(async () => {
  await fetchQueriedAddresses();
});
</script>

<template>
  <RuiMenu
    v-model="open"
    :options="{ placement: 'bottom-end' }"
    :menu-label="t('nft_settings.title')"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :options="{ placement: 'bottom' }"
        :open-delay="250"
        :close-delay="0"
      >
        <template #activator>
          <RuiButton
            v-bind="attrs"
            variant="text"
            icon
            class="text-rui-text-secondary!"
            data-testid="nft-settings"
            :aria-label="t('nft_settings.title')"
          >
            <RuiIcon name="lu-sliders-horizontal" />
          </RuiButton>
        </template>
        {{ t('nft_settings.title') }}
      </RuiTooltip>
    </template>

    <div class="w-[26rem] max-w-full p-4 flex flex-col gap-4">
      <section
        class="flex items-start justify-between gap-4"
        data-testid="nft-settings-addresses"
      >
        <div class="min-w-0">
          <h3 class="text-subtitle-2 font-medium m-0">
            {{ t('nft_settings.addresses.title') }}
          </h3>
          <p class="text-body-2 text-rui-text-secondary m-0 mt-0.5">
            {{ queriedCount === 0 ? t('nft_settings.addresses.all') : t('nft_settings.addresses.some', { count: queriedCount }) }}
          </p>
        </div>
        <RuiButton
          size="sm"
          variant="outlined"
          color="primary"
          class="shrink-0"
          data-testid="nft-settings-manage-addresses"
          @click="openAddresses()"
        >
          {{ t('nft_settings.addresses.manage') }}
        </RuiButton>
      </section>

      <RuiDivider />

      <section data-testid="nft-settings-images">
        <h3 class="text-subtitle-2 font-medium m-0">
          {{ t('nft_settings.images.title') }}
        </h3>
        <i18n-t
          scope="global"
          tag="p"
          class="text-body-2 text-rui-text-secondary m-0 mt-0.5 mb-3"
          keypath="general_settings.nft_setting.subtitle.nft_images_rendering_setting_hint"
        >
          <template #link>
            <ExternalLink
              color="primary"
              :url="externalLinks.nftWarning"
            >
              {{ t('common.here') }}
            </ExternalLink>
          </template>
        </i18n-t>
        <NftImageRenderingSetting />
      </section>
    </div>
  </RuiMenu>

  <QueriedAddressDialog
    v-if="manageAddresses"
    :module="Module.NFTS"
    @close="manageAddresses = false"
  />
</template>
