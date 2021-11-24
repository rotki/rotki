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
          {{ $t('statistics_graph_settings.save') }}
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
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { SettingsUpdate } from '@/types/user';

export default defineComponent({
  name: 'StatisticsGraphSettings',
  components: { MenuTooltipButton },
  emits: ['updated'],
  setup(_, { emit }) {
    const multiplier = ref('0');
    const visible = ref(false);
    const numericMultiplier = computed(() => {
      const multi = parseInt(multiplier.value);
      return isNaN(multi) ? 0 : multi;
    });
    const invalid = computed(() => {
      const numericValue = parseInt(multiplier.value);
      return isNaN(numericValue) || numericValue < 0;
    });
    const store = useStore();
    const updateSetting = async () => {
      await store.dispatch('session/settingsUpdate', {
        ssf0graphMultiplier: numericMultiplier.value
      } as SettingsUpdate);
      emit('updated');
      visible.value = false;
    };

    const multiplierSetting = computed(() => {
      const { session }: RotkehlchenState = store.state;
      const { ssf0graphMultiplier } = session!!.generalSettings;
      return ssf0graphMultiplier.toString();
    });

    const period = computed(() => {
      const { session }: RotkehlchenState = store.state;
      const { balanceSaveFrequency } = session!!.generalSettings;
      const multi = numericMultiplier.value;
      if (multi <= 0) {
        return 0;
      }
      return multi * balanceSaveFrequency;
    });

    onMounted(() => {
      multiplier.value = multiplierSetting.value;
    });

    watch(multiplierSetting, value => (multiplier.value = value.toString()));

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
