<script setup lang="ts">
import type { FintsBank } from '@/modules/banks/fints-bank-directory';
import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';

type BankSecretField = BankManifest['secrets'][number];

const credentials = defineModel<Record<string, string>>('credentials', { required: true });
const name = defineModel<string>('name', { required: true });

const { bank, errors, manifest, manual = false } = defineProps<{
  bank?: FintsBank;
  errors: (path: string) => string[];
  manifest: BankManifest;
  manual?: boolean;
}>();

const { connections } = storeToRefs(useBankConnectionsStore());
const { t } = useI18n({ useScope: 'global' });

const CLOSED = -1;
const OPEN = 0;

const suggestedName = ref<string>();
const nameCustomized = ref<boolean>(get(name).trim() !== '');
const advancedOpen = ref<number>(manual ? OPEN : CLOSED);

const advancedErrorCount = computed<number>(() => [
  'name',
  'credentials.bank_code',
  'credentials.endpoint',
].filter(path => errors(path).length > 0).length);

function secret(slot: string): BankSecretField | undefined {
  return manifest.secrets.find(field => field.slot === slot);
}

function uniqueName(base: string, existing: readonly BankConnection[]): string {
  const names = new Set(existing.filter(connection => connection.connector === 'fints').map(connection => connection.name));
  if (!names.has(base))
    return base;
  let suffix = 2;
  while (names.has(`${base} (${suffix})`))
    suffix++;
  return `${base} (${suffix})`;
}

function selectBank(bank: FintsBank | undefined): void {
  if (!bank)
    return;

  get(credentials).bank_code = bank.bankCodes.length === 1 ? bank.bankCodes[0] ?? '' : '';
  get(credentials).endpoint = bank.endpoint;
  if (!get(nameCustomized) || get(name) === get(suggestedName)) {
    const nextName = uniqueName(bank.name, get(connections));
    set(suggestedName, nextName);
    set(name, nextName);
  }
}

function updateName(value: string): void {
  set(name, value);
  set(nameCustomized, value.trim() !== '' && value !== get(suggestedName));
}

watch(advancedErrorCount, (count, previous) => {
  if (count > 0 && previous === 0)
    set(advancedOpen, OPEN);
});

watch(() => bank, selectBank, { immediate: true });

watch(() => manual, (value) => {
  if (value)
    set(advancedOpen, OPEN);
}, { immediate: true });
</script>

<template>
  <RuiMenuSelect
    v-if="bank && bank.bankCodes.length > 1"
    v-model="credentials.bank_code"
    :options="bank.bankCodes"
    :label="secret('bank_code')?.label"
    :error-messages="errors('credentials.bank_code')"
    data-testid="fints-bank-code"
  />

  <RuiTextField
    v-model="credentials.username"
    color="primary"
    :label="secret('username')?.label"
    :hint="secret('username')?.description"
    :error-messages="errors('credentials.username')"
    data-testid="bank-connection-secret-username"
  />
  <RuiRevealableTextField
    v-model="credentials.pin"
    color="primary"
    :label="secret('pin')?.label"
    :hint="secret('pin')?.description"
    :error-messages="errors('credentials.pin')"
    data-testid="bank-connection-secret-pin"
  />

  <RuiAccordions v-model="advancedOpen">
    <RuiAccordion eager>
      <template #header>
        <div class="flex items-center gap-2">
          {{ t('bank_settings.form.advanced') }}
          <RuiChip
            v-if="advancedErrorCount > 0"
            size="sm"
            color="error"
          >
            {{ advancedErrorCount }}
          </RuiChip>
        </div>
      </template>
      <div class="flex flex-col gap-4 py-2">
        <RuiTextField
          :model-value="name"
          color="primary"
          :label="t('bank_settings.form.name')"
          :hint="t('bank_settings.form.name_hint')"
          :error-messages="errors('name')"
          data-testid="bank-connection-name"
          @update:model-value="updateName($event)"
        />
        <RuiTextField
          v-model="credentials.bank_code"
          color="primary"
          :label="secret('bank_code')?.label"
          :hint="secret('bank_code')?.description"
          :error-messages="errors('credentials.bank_code')"
          data-testid="bank-connection-secret-bank_code"
        />
        <RuiTextField
          v-model="credentials.endpoint"
          color="primary"
          :label="secret('endpoint')?.label"
          :hint="secret('endpoint')?.description"
          :error-messages="errors('credentials.endpoint')"
          data-testid="bank-connection-secret-endpoint"
        />
      </div>
    </RuiAccordion>
  </RuiAccordions>
</template>
