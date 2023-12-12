<script setup lang="ts">
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
    events: false,
    timeStart: 0,
    timeEnd: 0,
    found: undefined,
    entriesFoundTotal: undefined
  }
);

const { t } = useI18n();
const { xs } = useDisplay();
</script>

<template>
  <tr class="bg-transparent">
    <td :colspan="xs ? 2 : colspan" class="font-medium py-2">
      <i18n
        v-if="events"
        path="upgrade_row.events"
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
          <DateDisplay class="mx-1" :timestamp="timeStart" />
        </template>
        <template #to>
          <DateDisplay class="ml-1" :timestamp="timeEnd" />
        </template>
      </i18n>
      <i18n v-else tag="div" path="upgrade_row.upgrade" class="md:text-center">
        <template #total>
          {{ entriesFoundTotal ? entriesFoundTotal : total }}
        </template>
        <template #limit>
          {{ found ? found : limit }}
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
      </i18n>
    </td>
  </tr>
</template>
