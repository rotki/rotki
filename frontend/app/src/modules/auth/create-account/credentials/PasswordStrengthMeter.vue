<script setup lang="ts">
import { PasswordIssue } from '@/modules/auth/create-account/credentials/password-patterns';
import {
  type PasswordRating,
  PasswordStrength,
  ratePassword,
  strengthScore,
} from '@/modules/auth/create-account/credentials/password-strength';

const { password, username = '' } = defineProps<{
  password: string;
  username?: string;
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

const rating = computed<PasswordRating>(() => ratePassword(password, username));

const strength = computed<PasswordStrength>(() => get(rating).strength);

const score = computed<number>(() => strengthScore(get(strength)));

function strengthAdvice(strength: PasswordStrength): string {
  switch (strength) {
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
}

function strengthLabel(strength: PasswordStrength): string {
  switch (strength) {
    case PasswordStrength.FAIR:
      return t('create_account.password_strength.label.fair');
    case PasswordStrength.GOOD:
      return t('create_account.password_strength.label.good');
    default:
      return t('create_account.password_strength.label.weak');
  }
}

function issueTip(issue: PasswordIssue): string {
  switch (issue) {
    case PasswordIssue.COMMON_WORD:
      return t('create_account.password_strength.issue.common_word');
    case PasswordIssue.CONTAINS_USERNAME:
      return t('create_account.password_strength.issue.contains_username');
    case PasswordIssue.DIGITS_ONLY:
      return t('create_account.password_strength.issue.digits_only');
    case PasswordIssue.REPEATS:
      return t('create_account.password_strength.issue.repeats');
    case PasswordIssue.SEQUENCE:
      return t('create_account.password_strength.issue.sequence');
  }
}

const advice = computed<string>(() => {
  const { issue, strength } = get(rating);
  if (!issue)
    return strengthAdvice(strength);
  return t('create_account.password_strength.rated', { strength: strengthLabel(strength), tip: issueTip(issue) });
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
    :data-issue="rating.issue"
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
