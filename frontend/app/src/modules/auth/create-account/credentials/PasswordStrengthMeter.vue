<script setup lang="ts">
import {
  PasswordStrength,
  passwordStrength,
  strengthScore,
} from '@/modules/auth/create-account/credentials/password-strength';

const { password } = defineProps<{
  password: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const SEGMENTS = [1, 2, 3, 4] as const;

const FILL: Record<PasswordStrength, string> = {
  empty: '',
  fair: 'bg-rui-warning',
  good: 'bg-rui-primary',
  strong: 'bg-rui-success',
  weak: 'bg-rui-error',
};

const strength = computed<PasswordStrength>(() => passwordStrength(password));

const score = computed<number>(() => strengthScore(get(strength)));

const advice = computed<string>(() => {
  switch (get(strength)) {
    case PasswordStrength.WEAK:
      return t('create_account.password_strength.weak');
    case PasswordStrength.FAIR:
      return t('create_account.password_strength.fair');
    case PasswordStrength.GOOD:
      return t('create_account.password_strength.good');
    case PasswordStrength.STRONG:
      return t('create_account.password_strength.strong');
    default:
      return t('create_account.password_strength.empty');
  }
});

function segmentClass(segment: number): string {
  return segment <= get(score) ? FILL[get(strength)] : 'bg-rui-grey-300 dark:bg-rui-grey-800';
}
</script>

<template>
  <div
    class="flex flex-col gap-1.5"
    data-testid="create-account-password-strength"
    :data-strength="strength"
  >
    <div
      class="flex gap-1"
      aria-hidden="true"
    >
      <div
        v-for="segment in SEGMENTS"
        :key="segment"
        class="h-1 flex-1 rounded-full transition-colors"
        :class="segmentClass(segment)"
      />
    </div>
    <p
      class="text-caption text-rui-text-secondary min-h-[2lh]"
      aria-live="polite"
    >
      {{ advice }}
    </p>
  </div>
</template>
