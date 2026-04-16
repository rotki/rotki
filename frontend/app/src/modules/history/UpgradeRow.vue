<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { usePremium } from '@/modules/premium/use-premium';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { events, entriesFoundTotal, found, total, limit } = defineProps<{
  colspan: number;
  label: string;
  total: number;
  limit: number;
  events?: boolean;
  timeStart?: number;
  timeEnd?: number;
  found?: number;
  entriesFoundTotal?: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();

// Linter hints: Ensure all keys are detectable by calling t() with explicit strings
if (false as boolean) {
  t('upgrade_row.events');
  t('upgrade_row.events_premium');
  t('upgrade_row.upgrade');
  t('upgrade_row.upgrade_premium');
}

const messageKey = computed<string>(() => {
  const isPremium = get(premium);
  if (events)
    return isPremium ? 'upgrade_row.events_premium' : 'upgrade_row.events';

  return isPremium ? 'upgrade_row.upgrade_premium' : 'upgrade_row.upgrade';
});

const linkText = computed<string>(() => {
  const isPremium = get(premium);
  return isPremium
    ? t('upgrade_row.upgrade_your_plan')
    : t('upgrade_row.rotki_premium');
});

const linkUrl = computed<string | undefined>(() => {
  const isPremium = get(premium);
  return isPremium ? externalLinks.manageSubscriptions : undefined;
});

const displayTotal = computed<number>(() => entriesFoundTotal ?? total);
const displayLimit = computed<number>(() => found ?? limit);
</script>

<template>
  <tr class="bg-transparent">
    <td
      :colspan="colspan"
      class="font-medium py-2"
    >
      <i18n-t
        scope="global"
        :keypath="messageKey"
        tag="div"
        class="md:text-center"
      >
        <template #total>
          {{ displayTotal }}
        </template>
        <template #limit>
          {{ displayLimit }}
        </template>
        <template #label>
          {{ label }}
        </template>
        <template #link>
          <ExternalLink
            :text="linkText"
            :url="linkUrl"
            premium
            color="primary"
          />
        </template>
        <template
          v-if="events"
          #from
        >
          <DateDisplay
            class="mx-1"
            :timestamp="timeStart || 0"
          />
        </template>
        <template
          v-if="events"
          #to
        >
          <DateDisplay
            class="ml-1"
            :timestamp="timeEnd || 0"
          />
        </template>
      </i18n-t>
    </td>
  </tr>
</template>
