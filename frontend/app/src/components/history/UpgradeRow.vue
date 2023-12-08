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
const { premiumURL } = useInterop();
const { xs } = useDisplay();
</script>

<template>
  <tr class="tr">
    <td :colspan="xs ? 2 : colspan" class="upgrade-row font-medium">
      <i18n
        v-if="events"
        tag="span"
        path="upgrade_row.events"
        class="flex flex-row justify-center items-end"
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
          <BaseExternalLink
            class="ml-1"
            :text="t('upgrade_row.rotki_premium')"
            :href="premiumURL"
          />
        </template>
        <template #from>
          <DateDisplay class="mx-1" :timestamp="timeStart" />
        </template>
        <template #to>
          <DateDisplay class="ms-1" :timestamp="timeEnd" />
        </template>
      </i18n>
      <i18n
        v-else
        tag="span"
        path="upgrade_row.upgrade"
        class="flex flex-row justify-center items-end"
      >
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
          <BaseExternalLink
            class="ml-1"
            :text="t('upgrade_row.rotki_premium')"
            :href="premiumURL"
          />
        </template>
      </i18n>
    </td>
  </tr>
</template>

<style>
.tr {
  background: transparent !important;
}

.upgrade-row {
  height: 60px;
}
</style>
