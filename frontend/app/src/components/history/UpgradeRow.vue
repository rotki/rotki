<template>
  <tr class="tr">
    <td
      :colspan="currentBreakpoint.xsOnly ? 2 : colspan"
      class="upgrade-row font-weight-medium"
    >
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
          <base-external-link
            class="ml-1"
            :text="tc('upgrade_row.rotki_premium')"
            :href="premiumURL"
          />
        </template>
        <template #from>
          <date-display class="mx-1" :timestamp="timeStart" />
        </template>
        <template #to>
          <date-display class="ms-1" :timestamp="timeEnd" />
        </template>
      </i18n>
      <i18n
        v-else
        tag="span"
        path="upgrade_row.upgrade"
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
          <base-external-link
            class="ml-1"
            :text="tc('upgrade_row.rotki_premium')"
            :href="premiumURL"
          />
        </template>
      </i18n>
    </td>
  </tr>
</template>
<script setup lang="ts">
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import { useTheme } from '@/composables/common';
import { useInterop } from '@/electron-interop';

defineProps({
  colspan: { required: true, type: Number },
  label: { required: true, type: String },
  total: { required: true, type: Number },
  limit: { required: true, type: Number },
  events: { required: false, type: Boolean, default: false },
  timeStart: { required: false, type: Number, default: 0 },
  timeEnd: { required: false, type: Number, default: 0 }
});

const { tc } = useI18n();
const { premiumURL } = useInterop();
const { currentBreakpoint } = useTheme();
</script>

<style>
.tr {
  background: transparent !important;
}

.upgrade-row {
  height: 60px;
}
</style>
