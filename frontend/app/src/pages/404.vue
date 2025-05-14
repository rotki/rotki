<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import { Routes } from '@/router/routes';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <NoDataScreen>
    <template #logo>
      <AppImage src="/assets/images/not-found.svg" />
    </template>
    <h5 class="text-h5 mb-4">
      {{ t('page_not_found.title') }}
    </h5>

    <InternalLink
      :to="Routes.DASHBOARD"
      class="text-decoration-none"
    >
      <RuiButton color="primary">
        <template #prepend>
          <RuiIcon
            name="lu-arrow-left"
            size="16"
          />
        </template>
        {{ t('page_not_found.back') }}
      </RuiButton>
    </internallink>
  </NoDataScreen>
</template>
