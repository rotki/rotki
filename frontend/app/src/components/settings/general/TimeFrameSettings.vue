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
      <v-col>
        <v-card class="pa-4" outlined>
          <div>
            <div class="text-subtitle-1">
              {{ $t('timeframe_settings.visible_timeframes') }}
            </div>

            <div class="timeframe-settings">
              <v-tooltip v-if="!premium" top>
                <template #activator="{ on, attrs }">
                  <v-icon small v-bind="attrs" v-on="on"> mdi-lock </v-icon>
                </template>
                <span v-text="$t('overall_balances.premium_hint')" />
              </v-tooltip>

              <v-chip
                v-for="(timeframe, i) in appendedVisibleTimeframes"
                :key="i"
                :class="activeClass(timeframe)"
                class="ma-2"
                small
                :close="
                  isTimeframesToggleable(timeframe) &&
                  !isTimeframeDisabled(timeframe) &&
                  selectableTimeframes.length > 1
                "
                :disabled="isTimeframeDisabled(timeframe)"
                @click:close="removeVisibleTimeframe(timeframe)"
                @click="timeframeChange(timeframe)"
              >
                {{ timeframe }}
              </v-chip>
            </div>
          </div>

          <template v-if="invisibleTimeframes.length > 0">
            <v-divider class="my-4" />

            <div>
              <div class="text-subtitle-1">
                {{ $t('timeframe_settings.inactive_timeframes') }}
              </div>
              <div class="timeframe-settings">
                <v-chip
                  v-for="(timeframe, i) in invisibleTimeframes"
                  :key="i"
                  class="ma-2"
                  small
                  close-icon="mdi-plus"
                  :close="isTimeframesToggleable(timeframe)"
                  :disabled="isTimeframeDisabled(timeframe)"
                  @click:close="addVisibleTimeframe(timeframe)"
                  @click="addVisibleTimeframe(timeframe)"
                >
                  {{ timeframe }}
                </v-chip>
              </div>
            </div>
          </template>
        </v-card>
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
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import { mapMutations } from 'vuex';
import Fragment from '@/components/helper/Fragment';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import SettingsMixin from '@/mixins/settings-mixin';
import { isPeriodAllowed } from '@/store/settings/utils';
import { LAST_KNOWN_TIMEFRAME } from '@/types/frontend-settings';

const validator = (value: any) =>
  Object.values(TimeFramePeriod).includes(value) ||
  value === TimeFramePersist.REMEMBER;

@Component({
  components: { TimeframeSelector, Fragment },
  methods: {
    ...mapMutations('session', ['setTimeframe'])
  }
})
export default class TimeFrameSettings extends Mixins(
  PremiumMixin,
  SettingsMixin
) {
  @Prop({ required: true, type: Object })
  message!: { error: string; success: string };

  @Prop({
    required: true,
    type: String,
    validator: validator
  })
  value!: TimeFrameSetting;

  @Prop({
    required: true,
    type: Array
  })
  visibleTimeframes!: TimeFramePeriod[];

  @Prop({
    required: true,
    type: String,
    validator: validator
  })
  currentSessionTimeframe!: TimeFramePeriod;
  setTimeframe!: (timeframe: TimeFramePeriod) => void;

  get appendedVisibleTimeframes() {
    return [TimeFramePersist.REMEMBER, ...this.visibleTimeframes] as const;
  }

  get invisibleTimeframes() {
    return this.timeframes.filter(item => {
      return !this.isTimeframeVisible(item);
    });
  }

  get selectableTimeframes() {
    return this.timeframes.filter(item => {
      return !this.isTimeframeDisabled(item) && this.isTimeframeVisible(item);
    });
  }

  get text(): string {
    const { success, error } = this.message;
    return success ? success : error;
  }

  get timeframes() {
    return Object.values(TimeFramePeriod);
  }

  worksWithoutPremium(period: TimeFrameSetting): boolean {
    return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
  }

  isTimeframeVisible(timeframe: TimeFramePeriod): boolean {
    return this.visibleTimeframes.includes(timeframe);
  }

  isTimeframesToggleable(timeframe: TimeFrameSetting) {
    return timeframe !== TimeFramePersist.REMEMBER;
  }

  isTimeframeDisabled(timeframe: TimeFrameSetting) {
    return !this.premium && !this.worksWithoutPremium(timeframe);
  }

  activeClass(timeframePeriod: TimeFrameSetting): string {
    return timeframePeriod === this.value ? 'timeframe-settings--active' : '';
  }

  addVisibleTimeframe(timeframe: TimeFramePeriod) {
    this.updateVisibleTimeframes([...this.visibleTimeframes, timeframe]);
  }

  removeVisibleTimeframe(timeframe: TimeFrameSetting) {
    if (timeframe === this.value) {
      this.timeframeChange(TimeFramePersist.REMEMBER);
    }
    this.updateVisibleTimeframes(
      this.visibleTimeframes.filter(item => {
        return item !== timeframe;
      }),
      timeframe === this.currentSessionTimeframe
    );
  }

  updateVisibleTimeframes(
    timeframes: TimeFramePeriod[],
    replaceCurrentSessionTimeframe: boolean = false
  ) {
    timeframes.sort((a: TimeFramePeriod, b: TimeFramePeriod) => {
      return this.timeframes.indexOf(a) - this.timeframes.indexOf(b);
    });

    if (replaceCurrentSessionTimeframe) {
      const value = timeframes[0];

      this.setTimeframe(value);
      this.updateSetting({ [LAST_KNOWN_TIMEFRAME]: value });
    }

    this.visibleTimeframesChange(timeframes);
  }

  @Emit()
  timeframeChange(_timeframe: TimeFrameSetting) {}

  @Emit()
  visibleTimeframesChange(_timeframes: TimeFrameSetting[]) {}
}
</script>
<style scoped lang="scss">
.timeframe-settings {
  ::v-deep {
    .v-chip {
      cursor: pointer;
    }
  }

  &--active {
    color: white !important;
    background-color: var(--v-primary-base) !important;
  }
}
</style>
