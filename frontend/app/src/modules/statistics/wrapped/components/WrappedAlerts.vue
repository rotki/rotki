<script setup lang="ts">
import { useHistorySyncStatus } from '@/modules/history/sync-status/use-history-sync-status';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

defineProps<{
  refreshing: boolean;
  premium: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * History freshness as a quiet line, and only when it matters: while history refreshes, or once it is
 * older than the out-of-sync period the user set. A recent sync says nothing.
 */
const { isNeverQueried, lastQueriedTimestamp, outOfSync } = useHistorySyncStatus();
</script>

<template>
  <div
    v-if="refreshing || outOfSync"
    class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-rui-text-secondary"
    data-testid="wrapped-sync-note"
  >
    <template v-if="refreshing">
      <RuiProgress
        circular
        variant="indeterminate"
        color="primary"
        size="14"
        thickness="2"
      />
      {{ t('wrapped.loading') }}
    </template>
    <template v-else>
      <RuiIcon
        name="lu-history"
        size="16"
      />
      <span v-if="isNeverQueried">{{ t('wrapped.sync.never') }}</span>
      <i18n-t
        v-else
        scope="global"
        keypath="wrapped.sync.stale"
        tag="span"
      >
        <template #time>
          <TimeAgoDisplay
            :timestamp="lastQueriedTimestamp"
            milliseconds
          />
        </template>
      </i18n-t>
      <RouterLink
        :to="{ name: '/history/events/' }"
        class="text-rui-primary hover:underline"
      >
        {{ t('wrapped.sync.action') }}
      </RouterLink>
    </template>
  </div>

  <RuiAlert
    v-if="!premium"
    type="info"
    class="py-1 [&>div]:items-center"
  >
    <div class="flex justify-between items-center">
      {{ t('wrapped.premium_nudge') }}
      <ExternalLink
        premium
        custom
      >
        <RuiButton color="primary">
          {{ t('wrapped.get_rotki_premium') }}
          <template #append>
            <RuiIcon
              name="lu-external-link"
              size="12"
            />
          </template>
        </RuiButton>
      </ExternalLink>
    </div>
  </RuiAlert>
</template>
