<template>
  <span class="date-display" :class="!shouldShowAmount ? 'blur-content' : null">
    {{ formatDate(displayTimestamp, dateFormat) }}
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import { displayDateFormatter } from '@/data/date_formatter';

@Component({
  computed: {
    ...mapGetters('session', ['dateDisplayFormat', 'shouldShowAmount']),
    ...mapState('session', ['scrambleData'])
  }
})
export default class DateDisplay extends Vue {
  @Prop({ required: true, type: Number })
  timestamp!: number;
  @Prop({ required: false, type: Boolean, default: false })
  noTimezone!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  noTime!: boolean;

  dateDisplayFormat!: string;
  shouldShowAmount!: boolean;
  scrambleData!: boolean;

  formatDate(value: number, format: string): string {
    return displayDateFormatter.format(new Date(value * 1000), format);
  }

  get dateFormat(): string {
    const display = this.noTimezone
      ? this.dateDisplayFormat.replace('%z', '').replace('%Z', '')
      : this.dateDisplayFormat;

    if (this.noTime) {
      return display.split(' ')[0];
    }
    return display;
  }

  get displayTimestamp(): number {
    if (!this.scrambleData) {
      return this.timestamp;
    }
    const start = new Date(2016, 0, 1).getTime();
    const now = Date.now();
    return new Date(start + Math.random() * (now - start)).getTime() / 1000;
  }
}
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
