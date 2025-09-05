<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';

interface Props {
  limit: number;
  premium: boolean;
  visibleCount: number;
}

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    v-if="!premium && visibleCount > 0"
    type="info"
  >
    <i18n-t
      scope="global"
      keypath="nft_gallery.upgrade"
      tag="span"
    >
      <template #limit>
        {{ limit }}
      </template>
      <template #link>
        <ExternalLink
          :text="t('upgrade_row.rotki_premium')"
          color="primary"
          premium
        />
      </template>
    </i18n-t>
  </RuiAlert>
</template>
