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
<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import { useSessionSettingsStore } from '@/store/settings/session';

type DefiProtocolInfo = {
  readonly identifier: string;
  readonly protocol: DefiProtocol;
};

const props = defineProps({
  item: { required: true, type: Object as PropType<DefiProtocolInfo> }
});
const { item } = toRefs(props);
const { scrambleData } = storeToRefs(useSessionSettingsStore());

const getIcon = ({ protocol }: DefiProtocolInfo): string => {
  return protocol.startsWith('makerdao') ? 'makerdao' : protocol;
};

const { t } = useI18n();

const identifier = computed<string>(() => {
  const { identifier } = get(item);
  if (get(scrambleData)) {
    if (parseInt(identifier)) {
      return t('defi_selector_item.vault').toString();
    } else if (identifier.includes('-')) {
      return identifier.split('-')[0];
    }
  }
  return identifier;
});
</script>
