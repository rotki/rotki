<template>
  <v-menu
    v-model="visible"
    max-width="300px"
    min-width="280px"
    left
    :close-on-content-click="false"
  >
    <template #activator="{ on }">
      <menu-tooltip-button
        :tooltip="$t('statistics_graph_settings.tooltip')"
        class-name="graph-period"
        :on-menu="on"
      >
        <v-icon>mdi-dots-vertical</v-icon>
      </menu-tooltip-button>
    </template>
    <card>
      <template #title>{{ $t('statistics_graph_settings.title') }}</template>
      <template #subtitle>
        {{ $t('statistics_graph_settings.subtitle') }}
      </template>
      <v-text-field
        v-model="multiplier"
        type="number"
        outlined
        :label="$t('statistics_graph_settings.label')"
      />

      <span v-if="period === 0">{{ $t('statistics_graph_settings.off') }}</span>
      <span v-else>{{ $t('statistics_graph_settings.on', { period }) }}</span>

      <template #buttons>
        <v-spacer />
        <v-btn
          depressed
          color="primary"
          :disabled="invalid"
          @click="updateSetting"
        >
          {{ $t('common.actions.save') }}
        </v-btn>
      </template>
    </card>
  </v-menu>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';

export default defineComponent({
  name: 'StatisticsGraphSettings',
  components: { MenuTooltipButton },
  emits: ['updated'],
  setup(_, { emit }) {
    const multiplier = ref('0');
    const visible = ref(false);
    const numericMultiplier = computed(() => {
      const multi = parseInt(get(multiplier));
      return isNaN(multi) ? 0 : multi;
    });
    const invalid = computed(() => {
      const numericValue = parseInt(get(multiplier));
      return isNaN(numericValue) || numericValue < 0;
    });

    const { update } = useSettingsStore();
    const { ssf0graphMultiplier, balanceSaveFrequency } = storeToRefs(
      useGeneralSettingsStore()
    );

    const updateSetting = async () => {
      await update({
        ssf0graphMultiplier: get(numericMultiplier)
      });
      emit('updated');
      set(visible, false);
    };

    const multiplierSetting = computed(() => {
      return get(ssf0graphMultiplier).toString();
    });

    const period = computed(() => {
      const multi = get(numericMultiplier);
      if (multi <= 0) {
        return 0;
      }
      return multi * get(balanceSaveFrequency);
    });

    onMounted(() => {
      set(multiplier, get(multiplierSetting));
    });

    watch(multiplierSetting, value => set(multiplier, value.toString()));

    return {
      invalid,
      visible,
      multiplier,
      period,
      updateSetting
    };
  }
});
</script>
