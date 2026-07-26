<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { msg } from '@/message-key';
import { usePremium } from '@/modules/premium/use-premium';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { range } = defineProps<{
  colspan: number;
  label: string;
  /** How many entries are shown, i.e. the premium limit. Rendered as `{limit}`. */
  limit: number;
  /** How many entries exist in total. Rendered as `{total}`. */
  total: number;
  /**
   * The processed time range. Its presence selects the `upgrade_row.events` wording, which is the
   * only message that interpolates `{from}`/`{to}`, so the variant and the timestamps it needs
   * cannot disagree.
   */
  range?: { timeStart: number; timeEnd: number };
}>();

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();

// Keys are branded via `msg.$t` so the i18n key-usage lint counts them despite the dynamic keypath.
const messageKey = computed<string>(() => {
  const isPremium = get(premium);
  if (range)
    return isPremium ? msg.$t('upgrade_row.events_premium') : msg.$t('upgrade_row.events');

  return isPremium ? msg.$t('upgrade_row.upgrade_premium') : msg.$t('upgrade_row.upgrade');
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
          {{ total }}
        </template>
        <template #limit>
          {{ limit }}
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
    </td>
  </tr>
</template>
