<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';

interface Props {
  justUpdated: boolean;
  isNeverQueried: boolean;
  longQuery: boolean;
  hasUndecodedTxs: any;
  lastQueriedDisplay: string;
  lastQueriedTimestamp: number;
}

const props = defineProps<Props>();

const {
  isNeverQueried,
  justUpdated,
  lastQueriedDisplay,
  lastQueriedTimestamp,
  longQuery,
} = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const [DefineTimeTooltip, ReuseTimeTooltip] = createReusableTemplate();
</script>

<template>
  <DefineTimeTooltip>
    <RuiTooltip
      :open-delay="400"
      persist-on-tooltip-hover
    >
      <template #activator>
        <span class="underline decoration-dotted cursor-help">
          {{ lastQueriedDisplay }}
        </span>
      </template>
      <DateDisplay
        :timestamp="lastQueriedTimestamp"
        hide-tooltip
        milliseconds
      />
    </RuiTooltip>
  </DefineTimeTooltip>

  <div>
    <template v-if="justUpdated">
      {{ t('dashboard.history_query_indicator.just_updated') }}
    </template>
    <template v-else-if="isNeverQueried">
      {{ t('dashboard.history_query_indicator.never_queried') }}
    </template>
    <i18n-t
      v-else-if="longQuery"
      keypath="dashboard.history_query_indicator.last_queried_long"
    >
      <template #time>
        <ReuseTimeTooltip />
      </template>
    </i18n-t>
    <i18n-t
      v-else-if="hasUndecodedTxs"
      keypath="dashboard.history_query_indicator.incomplete_decoding"
    >
      <template #time>
        <ReuseTimeTooltip />
      </template>
    </i18n-t>
    <i18n-t
      v-else
      keypath="dashboard.history_query_indicator.last_queried"
    >
      <template #time>
        <ReuseTimeTooltip />
      </template>
    </i18n-t>
  </div>
</template>
