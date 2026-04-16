<script setup lang="ts">
import HistoryEventsAlert from '@/modules/history/HistoryEventsAlert.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

defineProps<{
  refreshing: boolean;
  premium: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col gap-4">
    <HistoryEventsAlert />

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
