<template>
  <v-form :value="value" class="pt-4" @input="input">
    <div class="mb-4">
      <location-selector
        :value="form.location"
        :excludes="excludedLocations"
        outlined
        :label="$t('common.location')"
        :rules="locationRules"
        @input="updateForm({ location: $event })"
      />
    </div>
    <div class="mb-4">
      <amount-input
        :value="form.usdValue"
        outlined
        :label="
          $t('common.value_in_symbol', {
            symbol: currencySymbol
          })
        "
        :rules="valueRules"
        @input="updateForm({ usdValue: $event })"
      />
    </div>
  </v-form>
</template>
<script lang="ts">
import { defineComponent, PropType, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { setupGeneralSettings } from '@/composables/session';
import { LocationDataSnapshotPayload } from '@/store/balances/types';

export default defineComponent({
  name: 'EditLocationDataSnapshotForm',
  components: { LocationSelector },
  props: {
    value: {
      required: false,
      type: Boolean,
      default: false
    },
    form: {
      required: true,
      type: Object as PropType<LocationDataSnapshotPayload>
    },
    excludedLocations: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    }
  },
  emits: ['update:form', 'input'],
  setup(props, { emit }) {
    const { form } = toRefs(props);
    const { currencySymbol } = setupGeneralSettings();

    const input = (valid: boolean) => {
      emit('input', valid);
    };

    const updateForm = (partial: Partial<LocationDataSnapshotPayload>) => {
      emit('update:form', {
        ...(get(form) as LocationDataSnapshotPayload),
        ...partial
      });
    };

    return {
      currencySymbol,
      input,
      updateForm
    };
  },
  data() {
    return {
      locationRules: [
        (v: string) =>
          !!v ||
          this.$t(
            'dashboard.snapshot.edit.dialog.location_data.rules.location'
          ).toString()
      ],
      valueRules: [
        (v: string) =>
          !!v ||
          this.$t(
            'dashboard.snapshot.edit.dialog.location_data.rules.value'
          ).toString()
      ]
    };
  }
});
</script>
