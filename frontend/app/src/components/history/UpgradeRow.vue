<script setup lang="ts">
import { isDefined } from '@vueuse/shared';

withDefaults(
  defineProps<{
    colspan: number;
    label: string;
    total: number;
    limit: number;
    events?: boolean;
    timeStart?: number;
    timeEnd?: number;
    found: number;
    entriesFoundTotal?: number;
  }>(),
  {
    events: false,
    timeStart: 0,
    timeEnd: 0,
    entriesFoundTotal: undefined
  }
);

const { t } = useI18n();
const { premiumURL } = useInterop();
const { xs } = useDisplay();
</script>

<template>
  <tr class="tr">
    <td :colspan="xs ? 2 : colspan" class="upgrade-row font-weight-medium">
      <i18n
        v-if="events"
        tag="span"
        path="upgrade_row.events"
        class="d-flex flex-row justify-center align-end"
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
        class="d-flex flex-row justify-center align-end"
      >
        <template #total>
          {{ isDefined(entriesFoundTotal) ? entriesFoundTotal : total }}
        </template>
        <template #limit>
          {{ isDefined(entriesFoundTotal) ? found : limit }}
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
