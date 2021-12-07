<template>
  <div
    :class="{
      [$style.wrapper]: true,
      [$style.horizontal]: horizontal
    }"
  >
    <div class="font-weight-medium text-truncate">
      {{ truncateAddress(validator.publicKey, length) }}
    </div>
    <div>
      <span v-if="horizontal" :class="$style.divider"> - </span>
      <span v-else class="text-caption">
        {{ $t('validator_display.validator_index') }}
      </span>
      {{ validator.validatorIndex }}
    </div>
  </div>
</template>

<script lang="ts">
import { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { truncateAddress } from '@/filters';

export default defineComponent({
  name: 'ValidatorDisplay',
  props: {
    validator: {
      required: true,
      type: Object as PropType<Eth2ValidatorEntry>
    },
    horizontal: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const { horizontal } = toRefs(props);
    const length = computed(() => (horizontal.value ? 4 : 10));
    return {
      length,
      truncateAddress
    };
  }
});
</script>

<style lang="scss" module>
.wrapper {
  padding: 8px;
}

.divider {
  padding-left: 4px;
  padding-right: 4px;
}

.horizontal {
  display: flex;
  flex-direction: row;
}
</style>
