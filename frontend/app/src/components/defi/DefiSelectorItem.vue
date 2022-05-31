<template>
  <div class="d-flex flex-row align-center">
    <v-img
      aspect-ratio="1"
      contain
      position="left"
      width="26px"
      max-height="24px"
      :src="`/assets/images/defi/${getIcon(item)}.svg`"
    />
    <span class="ml-2">{{ identifier }}</span>
  </div>
</template>
<script lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { setupDisplayData } from '@/composables/session';
import i18n from '@/i18n';

type DefiProtocolInfo = {
  readonly identifier: string;
  readonly protocol: DefiProtocol;
};

export default defineComponent({
  name: 'DefiSelectorItem',
  props: {
    item: { required: true, type: Object as PropType<DefiProtocolInfo> }
  },
  setup(props) {
    const { item } = toRefs(props);

    const { scrambleData } = setupDisplayData();

    const getIcon = ({ protocol }: DefiProtocolInfo): string => {
      return protocol.startsWith('makerdao') ? 'makerdao' : protocol;
    };

    const identifier = computed<string>(() => {
      const { identifier } = get(item);
      if (get(scrambleData)) {
        if (parseInt(identifier)) {
          return i18n.t('defi_selector_item.vault').toString();
        } else if (identifier.includes('-')) {
          return identifier.split('-')[0];
        }
      }
      return identifier;
    });

    return {
      getIcon,
      identifier
    };
  }
});
</script>
