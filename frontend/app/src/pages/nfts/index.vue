<script setup lang="ts">
import { msg } from '@/message-key';
import NftGallery from '@/modules/balances/nft/NftGallery.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.nfts'), icon: 'lu-image', section: 1, order: 100, drawer: 'nfts' },
    noteLocation: NoteLocation.NFTS,
  },
});

const modules = [Module.NFTS];
const { enabled } = useModuleEnabled(modules[0]);
</script>

<template>
  <div
    v-if="!enabled"
    class="container"
  >
    <ModuleNotActive :modules="modules" />
  </div>
  <NftGallery
    v-else
    :modules="modules"
  />
</template>
