<script setup lang="ts">
import type { XpubPayload } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/api/types/errors';
import type { BtcChains } from '@/modules/onchain/chains';
import { Blockchain } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { createReusableTemplate } from '@vueuse/core';
import { isEmpty } from 'es-toolkit/compat';
import { type DetectionResult, detectXpubType, getKeyType, getPrefix, keyType, XpubPrefix, type XpubType } from '@/modules/accounts/xpub';
import { trimOnPaste } from '@/modules/common/helpers/event';
import { toMessages } from '@/modules/common/validation/validation';

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

const xpub = defineModel<XpubPayload | undefined>('xpub');

const { disabled, blockchain } = defineProps<{
  disabled: boolean;
  blockchain: BtcChains;
}>();

const emit = defineEmits<{
  'detected-address': [address: string];
}>();

const [DefineKeyTypeOption, ReuseKeyTypeOption] = createReusableTemplate<{ item: XpubType }>();

const { t } = useI18n({ useScope: 'global' });

const xpubKey = ref<string>('');
const derivationPath = ref<string>('');
const xpubKeyPrefix = ref<XpubPrefix>(XpubPrefix.XPUB);
const advanced = ref<boolean>(false);
const detectedType = ref<DetectionResult>();
const showDisambiguation = ref<boolean>(false);
const userOverride = ref<boolean>(false);
const pasteHandled = ref<boolean>(false);

function runDetection(value: string): void {
  const result = detectXpubType(value);
  set(detectedType, result);
  set(showDisambiguation, false);
  set(userOverride, false);

  if (result === 'address') {
    emit('detected-address', value.trim());
    return;
  }

  if (result === XpubPrefix.YPUB || result === XpubPrefix.ZPUB) {
    set(xpubKeyPrefix, result);
    return;
  }

  if (result === 'ambiguous') {
    if (blockchain === Blockchain.BCH) {
      set(xpubKeyPrefix, XpubPrefix.XPUB);
    }
    else {
      set(showDisambiguation, true);
    }
  }
}

function resolveDisambiguation(choice: XpubPrefix.XPUB | XpubPrefix.P2TR): void {
  set(xpubKeyPrefix, choice);
  set(detectedType, choice);
  set(showDisambiguation, false);
}

function onAdvancedPrefixChange(): void {
  set(userOverride, true);
  set(detectedType, undefined);
  set(showDisambiguation, false);
}

function onPasteXpub(event: ClipboardEvent): void {
  if (disabled)
    return;

  const paste = trimOnPaste(event);
  if (paste) {
    set(pasteHandled, true);
    set(xpubKey, paste);
    runDetection(paste);
  }
}

const keyTypeListData = computed<XpubType[]>(() => {
  if (blockchain === Blockchain.BTC)
    return keyType;

  return keyType.filter(item => ![XpubPrefix.ZPUB, XpubPrefix.P2TR].includes(item.value));
});

const autoDetected = computed<boolean>(() => {
  const detected = get(detectedType);
  if (get(userOverride) || !detected)
    return false;

  return detected !== 'ambiguous' && detected !== 'address';
});

function isAutoDetectedOption(option: XpubType): boolean {
  if (!get(autoDetected))
    return false;

  return option.value === get(xpubKeyPrefix);
}

const detectedHint = computed<string | undefined>(() => {
  if (!get(autoDetected))
    return undefined;

  const type = keyType.find(k => k.value === get(xpubKeyPrefix));
  return type ? t('account_form.xpub_detected.type_hint', { type: type.humanLabel }) : undefined;
});

const rules = {
  derivationPath: {
    basic: () => true,
  },
  xpub: {
    required: helpers.withMessage(t('account_form.validation.xpub_non_empty'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    derivationPath,
    xpub,
  },
  {
    $autoDirty: true,
    $externalResults: errors,
    $stopPropagation: true,
  },
);

function validate(): Promise<boolean> {
  return get(v$).$validate();
}

watch(errors, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

watchImmediate(xpub, (xpubVal: XpubPayload | undefined) => {
  set(xpubKey, xpubVal?.xpub || '');
  const prefix = getPrefix(xpubVal?.xpubType);
  if (prefix !== XpubPrefix.XPUB)
    set(xpubKeyPrefix, prefix);

  const derivation = get(derivationPath);
  if (derivation && derivation.replace(/'/g, '').replace(/\/$/, '') !== xpubVal?.derivationPath)
    set(derivationPath, xpubVal?.derivationPath || '');

  if (disabled && xpubVal?.xpub && xpubVal.xpubType) {
    const currentPrefix = getPrefix(xpubVal.xpubType);
    set(detectedType, currentPrefix);
  }
});

watch(() => blockchain, () => {
  set(xpubKeyPrefix, get(keyTypeListData)[0].value);
});

watch(xpubKey, (newKey) => {
  if (get(pasteHandled)) {
    set(pasteHandled, false);
    return;
  }

  if (newKey && !get(userOverride))
    runDetection(newKey);
  else if (!newKey)
    set(detectedType, undefined);
});

watch([xpubKeyPrefix, xpubKey, derivationPath], ([prefix, key, path]) => {
  let payload: XpubPayload | undefined;
  if (key) {
    payload = {
      derivationPath: path?.replace(/'/g, '').replace(/\/$/, '') ?? undefined,
      xpub: key.trim(),
      xpubType: getKeyType(prefix),
    };
  }
  set(xpub, payload);
});

defineExpose({
  validate,
});
</script>

<template>
  <DefineKeyTypeOption #default="{ item }">
    <div class="flex items-center gap-2">
      <span>{{ item.humanLabel }} ({{ item.label }})</span>
      <RuiChip
        v-if="isAutoDetectedOption(item)"
        color="success"
        size="sm"
        content-class="!leading-4"
      >
        {{ t('account_form.xpub_detected.badge') }}
      </RuiChip>
    </div>
  </DefineKeyTypeOption>

  <div class="mt-2 flex flex-col gap-4">
    <div class="flex gap-4">
      <RuiTextField
        v-model="xpubKey"
        variant="outlined"
        color="primary"
        class="account-form__xpub flex-1"
        :label="t('account_form.labels.btc.xpub')"
        autocomplete="off"
        :hint="detectedHint"
        :error-messages="toMessages(v$.xpub)"
        :disabled="disabled"
        @blur="v$.xpub.$touch()"
        @paste="onPasteXpub($event)"
      />
      <div>
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <div class="account-form__advanced">
              <RuiButton
                variant="text"
                icon
                class="mt-1"
                @click="advanced = !advanced"
              >
                <RuiIcon
                  v-if="advanced"
                  name="lu-chevron-up"
                />
                <RuiIcon
                  v-else
                  name="lu-chevron-down"
                />
              </RuiButton>
            </div>
          </template>
          <span>
            {{ t('account_form.advanced_tooltip', advanced ? 0 : 1) }}
          </span>
        </RuiTooltip>
      </div>
    </div>

    <div
      v-if="showDisambiguation"
      class="flex flex-col gap-2 -mt-2 mb-3"
    >
      <span class="text-rui-text-secondary text-body-2">
        {{ t('account_form.xpub_detected.disambiguation_prompt') }}
      </span>
      <div class="flex gap-2">
        <RuiButton
          :variant="xpubKeyPrefix === XpubPrefix.XPUB ? 'default' : 'outlined'"
          color="primary"
          size="sm"
          :disabled="disabled"
          @click="resolveDisambiguation(XpubPrefix.XPUB)"
        >
          <div class="flex flex-col items-start">
            <span>{{ t('account_form.xpub_detected.legacy') }}</span>
            <span
              class="text-caption"
              :class="xpubKeyPrefix === XpubPrefix.XPUB ? 'opacity-70' : 'text-rui-text-secondary'"
            >
              {{ t('account_form.xpub_detected.legacy_description') }}
            </span>
          </div>
        </RuiButton>
        <RuiButton
          :variant="xpubKeyPrefix === XpubPrefix.P2TR ? 'default' : 'outlined'"
          color="primary"
          size="sm"
          :disabled="disabled"
          @click="resolveDisambiguation(XpubPrefix.P2TR)"
        >
          <div class="flex flex-col items-start">
            <span>{{ t('account_form.xpub_detected.taproot') }}</span>
            <span
              class="text-caption"
              :class="xpubKeyPrefix === XpubPrefix.P2TR ? 'opacity-70' : 'text-rui-text-secondary'"
            >
              {{ t('account_form.xpub_detected.taproot_description') }}
            </span>
          </div>
        </RuiButton>
      </div>
      <span
        v-if="!disabled"
        class="text-rui-text-secondary text-caption"
      >
        {{ t('account_form.xpub_detected.disambiguation_hint') }}
      </span>
    </div>

    <div
      v-if="advanced"
      class="flex flex-col gap-4"
    >
      <RuiMenuSelect
        v-model="xpubKeyPrefix"
        :options="keyTypeListData"
        :disabled="disabled"
        class="account-form__xpub-key-type"
        key-attr="value"
        text-attr="label"
        hide-details
        variant="outlined"
        :label="t('account_form.xpub_detected.type_override')"
        @update:model-value="onAdvancedPrefixChange()"
      >
        <template #selection="{ item }">
          <ReuseKeyTypeOption :item="item" />
        </template>
        <template #item="{ item }">
          <ReuseKeyTypeOption :item="item" />
        </template>
      </RuiMenuSelect>
      <RuiTextField
        v-model="derivationPath"
        variant="outlined"
        color="primary"
        class="account-form__derivation-path"
        :label="t('account_form.labels.btc.derivation_path')"
        :error-messages="toMessages(v$.derivationPath)"
        autocomplete="off"
        :disabled="disabled"
        :hint="t('common.optional')"
        @blur="v$.derivationPath.$touch()"
      />
    </div>
  </div>
</template>
