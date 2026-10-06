<script setup lang="ts">
import type { ContextColorsType } from '@rotki/ui-library';
import { msg } from '@/message-key';
import { useCountFormatter } from '@/modules/assets/amount-display/use-count-formatter';
import { usePlanUpgradeLink } from '@/modules/premium/use-plan-upgrade-link';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const {
  adding = false,
  limit,
  linkColor = 'primary',
  range,
  tag = 'span',
  total,
} = defineProps<{
  label: string;
  /** How many entries the plan covers. */
  limit: number;
  /** How many entries exist, including the ones past the limit. */
  total: number;
  /**
   * The processed time range of a report. Its presence selects `plan_limit.unprocessed`, the only
   * message that interpolates `{from}`/`{to}`.
   */
  range?: { timeStart: number; timeEnd: number };
  /** The limit is what blocks adding an entry, so the message says it is reached rather than what it hides. */
  adding?: boolean;
  linkClass?: string;
  linkColor?: ContextColorsType;
  tag?: string;
}>();

const { currentTier } = usePremiumHelper();
const { upgradeText, upgradeUrl } = usePlanUpgradeLink();
const { formatCount } = useCountFormatter();

const hidden = computed<number>(() => Math.max(total - limit, 0));

const messageKey = computed<string>(() => {
  if (range)
    return msg.$t('plan_limit.unprocessed');
  if (adding || get(hidden) === 0)
    return msg.$t('plan_limit.reached');
  return msg.$t('plan_limit.hidden');
});
</script>

<template>
  <i18n-t
    scope="global"
    :keypath="messageKey"
    :tag="tag"
  >
    <template #plan>
      {{ currentTier }}
    </template>
    <template #hidden>
      {{ formatCount(hidden) }}
    </template>
    <template #total>
      {{ formatCount(total) }}
    </template>
    <template #limit>
      {{ formatCount(limit) }}
    </template>
    <template #label>
      {{ label }}
    </template>
    <template #link>
      <ExternalLink
        :class="linkClass"
        :text="upgradeText"
        :url="upgradeUrl"
        premium
        :color="linkColor"
      />
    </template>
    <template
      v-if="range"
      #from
    >
      <DateDisplay
        class="mx-1"
        :timestamp="range.timeStart"
      />
    </template>
    <template
      v-if="range"
      #to
    >
      <DateDisplay
        class="ml-1"
        :timestamp="range.timeEnd"
      />
    </template>
  </i18n-t>
</template>
