<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { Routes } from '@/router/routes';

defineProps<{
  isFirstLoad: boolean;
  refreshing: boolean;
  premium: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiAlert
      v-if="isFirstLoad"
      type="info"
    >
      <i18n-t
        scope="global"
        keypath="wrapped.history_events_nudge"
      >
        <template #link>
          <RouterLink
            :to="Routes.HISTORY"
          >
            <span class="underline">{{ t('transactions.title') }}</span>
          </RouterLink>
        </template>
      </i18n-t>
    </RuiAlert>

    <RuiAlert
      v-if="refreshing"
      type="info"
    >
      {{ t('wrapped.loading') }}
    </RuiAlert>

    <RuiAlert
      v-if="!premium"
      type="info"
      class="py-1 [&>div]:items-center"
    >
      <div class="flex justify-between items-center">
        {{ t('wrapped.premium_nudge') }}
        <ExternalLink
          :text="t('wrapped.get_rotki_premium')"
          variant="default"
          premium
          class="!flex [&_span]:!no-underline !px-3 !py-2"
          color="primary"
        >
          <template #append>
            <RuiIcon
              name="lu-external-link"
              size="12"
            />
          </template>
        </ExternalLink>
      </div>
    </RuiAlert>
  </div>
</template>
