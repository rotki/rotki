<template>
  <fragment>
    <v-row>
      <v-col>
        <div
          class="text-h6"
          v-text="$t('timeframe_settings.default_timeframe')"
        />
        <div
          class="text-subtitle-1"
          v-text="$t('timeframe_settings.default_timeframe_description')"
        />
      </v-col>
    </v-row>
    <v-row align="center" justify="center">
      <v-col cols="auto">
        <timeframe-selector setting :value="value" @input="timeframeChange" />
      </v-col>
    </v-row>
    <v-row>
      <v-col
        :class="{
          'success--text': !!message.success,
          'error--text': !!message.error
        }"
        class="text-subtitle-2 general-settings__timeframe"
      >
        <div v-if="text" v-text="text" />
      </v-col>
    </v-row>
  </fragment>
</template>

<script lang="ts">
import {
  TimeFramePeriod,
  TimeFramePersist,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';

const validator = (value: any) =>
  Object.values(TimeFramePeriod).includes(value) ||
  value === TimeFramePersist.REMEMBER;

@Component({
  components: { TimeframeSelector, Fragment }
})
export default class TimeFrameSettings extends Vue {
  @Prop({ required: true, type: Object })
  message!: { error: string; success: string };

  @Prop({
    required: true,
    type: String,
    validator: validator
  })
  value!: TimeFrameSetting;

  get text(): string {
    const { success, error } = this.message;
    return success ? success : error;
  }

  @Emit()
  timeframeChange(_timeframe: TimeFrameSetting) {}
}
</script>

<style scoped lang="scss"></style>
