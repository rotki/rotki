<script setup lang="ts">
import type { ZodType } from 'zod';
import type { CexMapping } from '@/modules/assets/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { cexMappingSchema } from '@/modules/assets/admin/cex-mapping/cex-mapping-form';
import { useModelForm } from '@/modules/core/form/use-model-form';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import ExchangeInput from '@/modules/shell/components/inputs/ExchangeInput.vue';

const modelValue = defineModel<CexMapping>({ required: true });
const forAllExchanges = defineModel<boolean>('forAllExchanges', { required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { editMode = false, exchangeName } = defineProps<{
  editMode?: boolean;
  /** The exchange's own name for the asset, when known: the clue to what it is recognized as. */
  exchangeName?: string;
}>();

const EXCLUDED_EXCHANGES = [
  'binanceus',
  'coinbaseprime',
  'coinbasepro',
];

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => cexMappingSchema({
  asset: t('asset_management.cex_mapping.form.asset_non_empty'),
  location: t('asset_management.cex_mapping.form.location_non_empty'),
  locationSymbol: t('asset_management.cex_mapping.form.location_symbol_non_empty'),
}, get(forAllExchanges)));

const form = useModelForm<CexMapping>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
});

/** The input clears to `undefined`, which this payload spells `null`: a mapping for every exchange. */
const locationModel = computed<string | undefined>({
  get: () => form.state.location ?? undefined,
  set: (value?: string) => {
    form.state.location = value ?? null;
    form.touch('location');
  },
});

const mappingAlertInfo = computed<{ primary: string; related: string } | undefined>(() => {
  const currentLocation = form.state.location;
  if (!currentLocation || get(forAllExchanges))
    return undefined;

  if (currentLocation === 'binance')
    return { primary: 'binance', related: 'binanceus' };

  if (currentLocation === 'coinbase')
    return { primary: 'coinbase', related: 'coinbaseprime' };

  return undefined;
});

function checkPassedForm() {
  const data = get(modelValue);
  if (data) {
    set(forAllExchanges, !data.location);
  }
  else {
    set(forAllExchanges, false);
  }
}

onBeforeMount(() => {
  checkPassedForm();
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <dl
      v-if="editMode"
      class="grid grid-cols-2 gap-4 m-0 mb-4 rounded-rui-control border border-rui-divider px-4 py-3"
      data-testid="cex-mapping-summary"
    >
      <div class="flex flex-col gap-1">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('common.exchange') }}
        </dt>
        <dd class="m-0">
          <LocationDisplay
            v-if="form.state.location"
            horizontal
            :open-details="false"
            :identifier="form.state.location"
          />
          <span
            v-else
            class="text-rui-text"
          >
            {{ t('asset_management.cex_mapping.all_exchanges') }}
          </span>
        </dd>
      </div>
      <div class="flex flex-col gap-1">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('asset_management.cex_mapping.location_symbol') }}
        </dt>
        <dd class="m-0 font-medium text-rui-text">
          {{ form.state.locationSymbol }}
        </dd>
      </div>
    </dl>
    <template v-else>
      <RuiSwitch
        v-model="forAllExchanges"
        color="primary"
        class="mb-2"
      >
        {{ t('asset_management.cex_mapping.save_for_all') }}
      </RuiSwitch>
      <ExchangeInput
        v-if="!forAllExchanges"
        v-model="locationModel"
        :label="t('common.exchange')"
        :excludes="EXCLUDED_EXCHANGES"
        clearable
        :error-messages="form.errors('location')"
      />
      <RuiTextField
        v-model="form.state.locationSymbol"
        data-testid="location-symbol"
        color="primary"
        clearable
        :label="t('asset_management.cex_mapping.location_symbol')"
        :hint="exchangeName ? t('asset_management.cex_mapping.exchange_name', { name: exchangeName }) : undefined"
        :error-messages="form.errors('locationSymbol')"
        @update:model-value="form.touch('locationSymbol')"
      />
    </template>
    <AssetSelect
      v-model="form.state.asset"
      :label="t('asset_management.cex_mapping.recognized_as')"
      :error-messages="form.errors('asset')"
      @update:model-value="form.touch('asset')"
    />
    <RuiAlert
      v-if="mappingAlertInfo"
      type="info"
      class="mt-2"
    >
      <div class="flex items-center gap-1 dark:gap-2.5 -mt-0.5">
        {{ t('asset_management.cex_mapping.mapping_info_prefix') }}
        <LocationDisplay
          horizontal
          :open-details="false"
          class="[&>div]:gap-0.5 dark:[&>div]:gap-2"
          :identifier="mappingAlertInfo.primary"
        />
        {{ t('asset_management.cex_mapping.mapping_info_middle') }}
        <LocationDisplay
          horizontal
          :open-details="false"
          class="[&>div]:gap-0.5 dark:[&>div]:gap-2"
          :identifier="mappingAlertInfo.related"
        />
      </div>
    </RuiAlert>
  </div>
</template>
