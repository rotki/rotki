<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import HelpLink from '@/modules/shell/components/HelpLink.vue';

const coingecko = defineModel<string>('coingecko', { required: true });
const cryptocompare = defineModel<string>('cryptocompare', { required: true });

const { coingeckoErrors, cryptocompareErrors, disabled = false } = defineProps<{
  coingeckoErrors: string[];
  cryptocompareErrors: string[];
  disabled?: boolean;
}>();

const emit = defineEmits<{
  touch: [field: 'coingecko' | 'cryptocompare'];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTextField
    v-model="coingecko"
    data-testid="coingecko-input"
    variant="outlined"
    color="primary"
    clearable
    class="col-span-2"
    :hint="t('asset_form.labels.coingecko_hint')"
    :label="t('asset_form.labels.coingecko')"
    :error-messages="coingeckoErrors"
    :disabled="disabled"
    @update:model-value="emit('touch', 'coingecko')"
  >
    <template #append>
      <HelpLink
        small
        :url="externalLinks.contributeSection.coingecko"
        :tooltip="t('asset_form.help_coingecko')"
      />
    </template>
  </RuiTextField>
  <RuiTextField
    v-model="cryptocompare"
    data-testid="cryptocompare-input"
    variant="outlined"
    color="primary"
    clearable
    class="col-span-2"
    :label="t('asset_form.labels.cryptocompare')"
    :hint="t('asset_form.labels.cryptocompare_hint')"
    :error-messages="cryptocompareErrors"
    :disabled="disabled"
    @update:model-value="emit('touch', 'cryptocompare')"
  >
    <template #append>
      <HelpLink
        small
        :url="externalLinks.contributeSection.cryptocompare"
        :tooltip="t('asset_form.help_cryptocompare')"
      />
    </template>
  </RuiTextField>
</template>
