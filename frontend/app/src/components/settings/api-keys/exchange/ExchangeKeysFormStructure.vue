<script setup lang="ts">
interface SlotProps {
  label?: string;
  hint?: string;
  className?: string;
}

const props = defineProps<{
  location: string;
}>();

const slots = defineSlots<{
  apiKey: (props: SlotProps) => void;
  apiSecret: (props: SlotProps) => void;
  passphrase?: (props: SlotProps) => void;
}>();

const LOCATION_KEYS = ['apiKey', 'apiSecret', 'passphrase'] as const;

type LocationKey = typeof LOCATION_KEYS[number];

type LocationConfig = Partial<Record<LocationKey, SlotProps>>;

const { t } = useI18n({ useScope: 'global' });

const COINBASE_FORMATS = {
  apiKeyNameFormat: 'organizations/{org_id}/apiKeys/{key_id}',
  privateKeyFormat: '-----BEGIN EC PRIVATE KEY-----\\n{KEY}\\n-----END EC PRIVATE KEY-----\\n',
};

const customLabel: Record<string, LocationConfig> = {
  bitmex: {
    apiKey: {
      label: t('exchange_settings.inputs.id'),
    },
    apiSecret: {
      label: t('exchange_settings.inputs.secret'),
    },
  },
  coinbase: {
    apiKey: {
      hint: `${t('exchange_settings.inputs.format')}: ${COINBASE_FORMATS.apiKeyNameFormat}`,
      label: t('exchange_settings.inputs.api_key_name'),
    },
    apiSecret: {
      hint: `${t('exchange_settings.inputs.format')}: ${COINBASE_FORMATS.privateKeyFormat}`,
      label: t('exchange_settings.inputs.private_key'),
    },
  },
  coinbaseprime: {
    apiKey: {
      label: t('exchange_settings.inputs.access_key'),
    },
    apiSecret: {
      className: 'order-2',
      label: t('exchange_settings.inputs.signing_key'),
    },
    passphrase: {
      className: 'order-1',
      label: t('exchange_settings.inputs.passphrase'),
    },
  },
};

// Default data fallback
const defaultData: Record<LocationKey, SlotProps> = {
  apiKey: {
    label: t('exchange_settings.inputs.api_key'),
  },
  apiSecret: {
    label: t('exchange_settings.inputs.api_secret'),
  },
  passphrase: {
    label: t('exchange_settings.inputs.passphrase'),
  },
};

const slotData = computed(() => {
  const location = props.location;
  const locationConfig = customLabel[location] || {};

  return LOCATION_KEYS
    .map(name => ({
      bindings: {
        ...defaultData[name],
        ...locationConfig[name],
      },
      name,
      slot: slots[name],
    }))
    .filter(item => item.slot);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <slot
      v-for="item in slotData"
      :name="item.name"
      v-bind="item.bindings"
    />
  </div>
</template>
