<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';

withDefaults(
  defineProps<{
    colspan: number;
    label: string;
    total: number;
    limit: number;
    events?: boolean;
    timeStart?: number;
    timeEnd?: number;
    found?: number;
    entriesFoundTotal?: number;
  }>(),
  {
    entriesFoundTotal: undefined,
    events: false,
    found: undefined,
    timeEnd: 0,
    timeStart: 0,
  },
);

const { t } = useI18n();
</script>

<template>
  <tr class="bg-transparent">
    <td
      :colspan="colspan"
      class="font-medium py-2"
    >
      <i18n-t
        v-if="events"
        keypath="upgrade_row.events"
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
            :text="t('upgrade_row.rotki_premium')"
            premium
            color="primary"
          />
        </template>
        <template #from>
          <DateDisplay
            class="mx-1"
            :timestamp="timeStart"
          />
        </template>
        <template #to>
          <DateDisplay
            class="ml-1"
            :timestamp="timeEnd"
          />
        </template>
      </i18n-t>
      <i18n-t
        v-else
        tag="div"
        keypath="upgrade_row.upgrade"
        class="md:text-center"
      >
        <template #total>
          {{ entriesFoundTotal ? entriesFoundTotal : total }}
        </template>
        <template #limit>
          {{ found !== undefined ? found : limit }}
        </template>
        <template #label>
          {{ label }}
        </template>
        <template #link>
          <ExternalLink
            :text="t('upgrade_row.rotki_premium')"
            premium
            color="primary"
          />
        </template>
      </i18n-t>
    </td>
  </tr>
</template>
