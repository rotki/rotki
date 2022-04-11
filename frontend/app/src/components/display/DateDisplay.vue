<template>
  <span class="date-display" :class="{ 'blur-content': !shouldShowAmount }">
    {{ formattedDate }}
  </span>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { setupDisplayData, setupGeneralSettings } from '@/composables/session';
import { displayDateFormatter } from '@/data/date_formatter';

export default defineComponent({
  name: 'DateDisplay',
  props: {
    timestamp: { required: true, type: Number },
    noTimezone: { required: false, type: Boolean, default: false },
    noTime: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { timestamp, noTimezone, noTime } = toRefs(props);
    const { dateDisplayFormat } = setupGeneralSettings();
    const { scrambleData, shouldShowAmount } = setupDisplayData();

    const dateFormat = computed<string>(() => {
      const display = get(noTimezone)
        ? get(dateDisplayFormat).replace('%z', '').replace('%Z', '')
        : get(dateDisplayFormat);

      if (get(noTime)) {
        return display.split(' ')[0];
      }
      return display;
    });

    const displayTimestamp = computed<number>(() => {
      if (!get(scrambleData)) {
        return get(timestamp);
      }
      const start = new Date(2016, 0, 1).getTime();
      const now = Date.now();
      return new Date(start + Math.random() * (now - start)).getTime() / 1000;
    });

    const formattedDate = computed<string>(() => {
      return displayDateFormatter.format(
        new Date(get(displayTimestamp) * 1000),
        get(dateFormat)
      );
    });

    return {
      shouldShowAmount,
      formattedDate
    };
  }
});
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
