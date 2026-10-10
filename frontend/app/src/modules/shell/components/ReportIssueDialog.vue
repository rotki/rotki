<script setup lang="ts">
import { externalLinks, SUPPORT_EMAIL } from '@shared/external-links';
import { logger } from '@/modules/core/common/logging/logging';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import { usePrivacyMode } from '@/modules/settings/use-privacy';
import { useScrambleSetting } from '@/modules/settings/use-scramble-settings';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { githubIssueUrl, gmailComposeUrl, googleFormUrl, isSubmittable, type IssueDraft, MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH, supportMailtoUrl } from '@/modules/shell/components/report-issue-links';
import ReportIssueDiscordTip from '@/modules/shell/components/ReportIssueDiscordTip.vue';
import ReportIssueEmailButton from '@/modules/shell/components/ReportIssueEmailButton.vue';

const { close, initialDescription: storeDescription, initialTitle: storeTitle, visible } = useReportIssue();

const uiClasses = {
  tipCard: 'flex items-start gap-3 p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded',
  tipCardIcon: 'text-rui-text-secondary shrink-0 mt-0.5',
} as const;

const GOOGLE_FORM_URL = import.meta.env.VITE_GOOGLE_FORM_URL;
const GOOGLE_FORM_TITLE_ENTRY = import.meta.env.VITE_GOOGLE_FORM_TITLE_ENTRY;
const GOOGLE_FORM_DESCRIPTION_ENTRY = import.meta.env.VITE_GOOGLE_FORM_DESCRIPTION_ENTRY;

const { t } = useI18n({ useScope: 'global' });

const issueTitle = ref<string>('');
const issueDescription = ref<string>('');
const openError = ref<string>('');

const { showPrivacyModeMenu } = storeToRefs(useAreaVisibilityStore());

const { openUrl } = useInterop();
const { enabled: scrambleEnabled } = useScrambleSetting();
const { privacyMode } = usePrivacyMode();
const { copy } = useClipboard();

const isPrivacyEnabled = computed<boolean>(() => get(privacyMode) > 0 || get(scrambleEnabled));

const privacyStatusText = computed<string>(() => {
  const modes: string[] = [];

  if (get(privacyMode) === 1) {
    modes.push(t('help_sidebar.report_issue.dialog.tips.screenshot.semi_private'));
  }
  else if (get(privacyMode) === 2) {
    modes.push(t('help_sidebar.report_issue.dialog.tips.screenshot.private'));
  }

  if (get(scrambleEnabled)) {
    modes.push(t('help_sidebar.report_issue.dialog.tips.screenshot.scramble'));
  }

  return modes.join(', ');
});

const draft = computed<IssueDraft>(() => ({
  description: get(issueDescription),
  title: get(issueTitle),
}));

const isFormValid = computed<boolean>(() => isSubmittable(get(draft)));

const titleCharCount = computed<number>(() => get(issueTitle).length);
const descriptionCharCount = computed<number>(() => get(issueDescription).length);

function closeDialog(): void {
  close();
  set(issueTitle, '');
  set(issueDescription, '');
  set(openError, '');
}

/** The draft is cleared only once the target app or form accepted it. */
async function openUrlAndClose(url: string, failureMessage: string): Promise<void> {
  set(openError, '');
  try {
    await openUrl(url);
  }
  catch (error: unknown) {
    logger.error(error);
    set(openError, failureMessage);
    return;
  }
  closeDialog();
}

async function submitViaGithub(): Promise<void> {
  await openUrlAndClose(
    githubIssueUrl(get(draft)),
    t('help_sidebar.report_issue.dialog.open_failed.generic'),
  );
}

async function submitViaGoogleForm(): Promise<void> {
  await openUrlAndClose(
    googleFormUrl(get(draft), {
      descriptionEntry: GOOGLE_FORM_DESCRIPTION_ENTRY,
      titleEntry: GOOGLE_FORM_TITLE_ENTRY,
      url: GOOGLE_FORM_URL,
    }),
    t('help_sidebar.report_issue.dialog.open_failed.generic'),
  );
}

async function submitViaEmail(): Promise<void> {
  await openUrlAndClose(
    supportMailtoUrl(get(draft)),
    t('help_sidebar.report_issue.dialog.open_failed.email'),
  );
}

function openDiscord(): void {
  openUrl(externalLinks.discord);
}

function openPrivacyModeMenu(): void {
  set(showPrivacyModeMenu, true);
  closeDialog();
}

function copyEmail(): void {
  copy(SUPPORT_EMAIL);
}

async function openGmail(): Promise<void> {
  await openUrlAndClose(
    gmailComposeUrl(get(draft)),
    t('help_sidebar.report_issue.dialog.open_failed.generic'),
  );
}

onMounted(() => {
  set(issueTitle, get(storeTitle));
  set(issueDescription, get(storeDescription));
});
</script>

<template>
  <RuiDialog
    v-model="visible"
    max-width="600"
    persistent
  >
    <RuiCard
      :class-names="{ content: '!pt-1.5' }"
      class="max-h-[90vh]"
    >
      <template #header>
        {{ t('help_sidebar.report_issue.dialog.title') }}
      </template>
      <template #subheader>
        {{ t('help_sidebar.report_issue.dialog.description') }}
      </template>

      <div class="flex flex-col gap-4">
        <RuiTextField
          v-model="issueTitle"
          :label="t('help_sidebar.report_issue.dialog.form.title.label')"
          :hint="t('help_sidebar.report_issue.dialog.form.title.hint', { count: titleCharCount, max: MAX_TITLE_LENGTH })"
          :maxlength="MAX_TITLE_LENGTH"
          variant="outlined"
          dense
          class="!text-sm"
          color="primary"
        />

        <RuiTextArea
          v-model="issueDescription"
          :label="t('help_sidebar.report_issue.dialog.form.description.label')"
          :hint="t('help_sidebar.report_issue.dialog.form.description.hint', { count: descriptionCharCount, max: MAX_DESCRIPTION_LENGTH })"
          :maxlength="MAX_DESCRIPTION_LENGTH"
          variant="outlined"
          color="primary"
          class="!text-sm"
          min-rows="4"
          max-rows="8"
        />

        <div class="flex flex-col gap-2">
          <span class="text-sm font-medium">
            {{ t('help_sidebar.report_issue.dialog.submit_options.title') }}
          </span>
          <div class="flex flex-wrap gap-2">
            <RuiButton
              variant="outlined"
              color="primary"
              :disabled="!isFormValid"
              data-testid="report-issue-github"
              @click="submitViaGithub()"
            >
              <template #prepend>
                <RuiIcon name="lu-github" />
              </template>
              {{ t('help_sidebar.report_issue.dialog.submit_options.github') }}
            </RuiButton>
            <RuiButton
              variant="outlined"
              color="primary"
              :disabled="!isFormValid"
              data-testid="report-issue-google-form"
              @click="submitViaGoogleForm()"
            >
              <template #prepend>
                <RuiIcon name="lu-file-text" />
              </template>
              {{ t('help_sidebar.report_issue.dialog.submit_options.google_form') }}
            </RuiButton>
            <ReportIssueEmailButton
              :email="SUPPORT_EMAIL"
              :is-form-valid="isFormValid"
              @submit-email="submitViaEmail()"
              @copy-email="copyEmail()"
              @open-gmail="openGmail()"
            />
          </div>
          <RuiAlert
            v-if="openError"
            type="error"
            variant="outlined"
            data-testid="report-issue-open-error"
          >
            {{ openError }}
          </RuiAlert>
          <span class="text-xs text-rui-text-secondary flex items-center gap-1">
            <RuiIcon
              name="lu-info"
              size="14"
            />
            {{ t('help_sidebar.report_issue.dialog.submit_options.privacy_note') }}
          </span>
        </div>

        <RuiDivider />

        <div class="flex flex-col gap-3">
          <span class="text-sm font-medium flex items-center gap-1">
            <RuiIcon
              name="lu-lightbulb"
              size="16"
            />
            {{ t('help_sidebar.report_issue.dialog.tips.title') }}
          </span>

          <ReportIssueDiscordTip @open-discord="openDiscord()" />

          <div :class="uiClasses.tipCard">
            <RuiIcon
              name="lu-camera"
              :class="uiClasses.tipCardIcon"
            />
            <div class="flex flex-col gap-1">
              <span class="text-sm">
                {{ t('help_sidebar.report_issue.dialog.tips.screenshot.title') }}
              </span>
              <span class="text-xs text-rui-text-secondary">
                {{ t('help_sidebar.report_issue.dialog.tips.screenshot.description') }}
              </span>
              <RuiButton
                v-if="!isPrivacyEnabled"
                variant="text"
                color="primary"
                size="sm"
                class="self-start -ml-1.5 !py-0"
                data-testid="report-issue-enable-privacy"
                @click="openPrivacyModeMenu()"
              >
                {{ t('help_sidebar.report_issue.dialog.tips.screenshot.action') }}
              </RuiButton>
              <span
                v-else
                class="text-xs text-rui-success flex items-center gap-1 py-1"
                data-testid="report-issue-privacy-status"
              >
                <RuiIcon
                  name="lu-check"
                  size="14"
                />
                {{ t('help_sidebar.report_issue.dialog.tips.screenshot.enabled_with_mode', { mode: privacyStatusText }) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          data-testid="report-issue-close"
          @click="closeDialog()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
