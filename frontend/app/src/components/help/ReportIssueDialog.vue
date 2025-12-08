<script setup lang="ts">
import { externalLinks, SUPPORT_EMAIL } from '@shared/external-links';
import { useInterop } from '@/composables/electron-interop';
import { usePrivacyMode } from '@/composables/privacy';
import { useScrambleSetting } from '@/composables/scramble-settings';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const modelValue = defineModel<boolean>({ required: true });
const props = defineProps<{
  initialTitle?: string;
  initialDescription?: string;
}>();

const MAX_TITLE_LENGTH = 100;
const MAX_DESCRIPTION_LENGTH = 1500;

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

const isFormValid = computed<boolean>(() => get(issueTitle).trim().length > 0);

const titleCharCount = computed<number>(() => get(issueTitle).length);
const descriptionCharCount = computed<number>(() => get(issueDescription).length);

const encodedTitle = computed<string>(() => encodeURIComponent(get(issueTitle).slice(0, MAX_TITLE_LENGTH)));
const encodedDescription = computed<string>(() => encodeURIComponent(get(issueDescription).slice(0, MAX_DESCRIPTION_LENGTH)));

function closeDialog(): void {
  set(modelValue, false);
  set(issueTitle, '');
  set(issueDescription, '');
}

function openUrlAndClose(url: string): void {
  openUrl(url);
  closeDialog();
}

function submitViaGithub(): void {
  openUrlAndClose(`${externalLinks.githubNewBugReport}&title=${get(encodedTitle)}&body=${get(encodedDescription)}`);
}

function submitViaGoogleForm(): void {
  openUrlAndClose(`${GOOGLE_FORM_URL}?${GOOGLE_FORM_TITLE_ENTRY}=${get(encodedTitle)}&${GOOGLE_FORM_DESCRIPTION_ENTRY}=${get(encodedDescription)}`);
}

function submitViaEmail(): void {
  openUrlAndClose(`mailto:${SUPPORT_EMAIL}?subject=${get(encodedTitle)}&body=${get(encodedDescription)}`);
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

function openGmail(): void {
  openUrlAndClose(`${externalLinks.gmailCompose}&to=${encodeURIComponent(SUPPORT_EMAIL)}&su=${get(encodedTitle)}&body=${get(encodedDescription)}`);
}

watch(modelValue, (isOpen) => {
  if (isOpen) {
    set(issueTitle, props.initialTitle ?? '');
    set(issueDescription, props.initialDescription ?? '');
  }
});
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="600"
    persistent
  >
    <RuiCard
      content-class="!pt-1.5"
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
              @click="submitViaGoogleForm()"
            >
              <template #prepend>
                <RuiIcon name="lu-file-text" />
              </template>
              {{ t('help_sidebar.report_issue.dialog.submit_options.google_form') }}
            </RuiButton>
            <div class="flex">
              <RuiButton
                variant="outlined"
                color="primary"
                class="!rounded-r-none !border-r-0"
                :disabled="!isFormValid"
                @click="submitViaEmail()"
              >
                <template #prepend>
                  <RuiIcon name="lu-mail" />
                </template>
                {{ t('help_sidebar.report_issue.dialog.submit_options.email') }}
              </RuiButton>
              <RuiMenu
                :popper="{ placement: 'bottom-end' }"
                close-on-content-click
              >
                <template #activator="{ attrs }">
                  <RuiButton
                    variant="outlined"
                    color="primary"

                    class="!rounded-l-none !px-2 h-9 -ml-[1px]"
                    v-bind="attrs"
                  >
                    <RuiIcon
                      name="lu-chevron-down"
                      size="16"
                    />
                  </RuiButton>
                </template>
                <div class="py-2">
                  <RuiButton
                    variant="list"
                    @click="copyEmail()"
                  >
                    <template #prepend>
                      <RuiIcon name="lu-copy" />
                    </template>
                    {{ t('help_sidebar.report_issue.dialog.submit_options.copy_email', { email: SUPPORT_EMAIL }) }}
                  </RuiButton>
                  <RuiButton
                    variant="list"
                    :disabled="!isFormValid"
                    @click="openGmail()"
                  >
                    <template #prepend>
                      <RuiIcon name="lu-mail" />
                    </template>
                    {{ t('help_sidebar.report_issue.dialog.submit_options.open_gmail') }}
                  </RuiButton>
                </div>
              </RuiMenu>
            </div>
          </div>
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

          <div :class="uiClasses.tipCard">
            <RuiIcon
              name="lu-discord"
              :class="uiClasses.tipCardIcon"
            />
            <div class="flex flex-col gap-1">
              <span class="text-sm">
                {{ t('help_sidebar.report_issue.dialog.tips.discord.title') }}
              </span>
              <i18n-t
                keypath="help_sidebar.report_issue.dialog.tips.discord.description"
                tag="span"
                class="text-xs text-rui-text-secondary"
                scope="global"
              >
                <template #channel>
                  <span class="font-mono">{{ t('help_sidebar.report_issue.dialog.tips.discord.channel') }}</span>
                </template>
              </i18n-t>
              <RuiButton
                variant="text"
                color="primary"
                size="sm"
                class="self-start -ml-1.5 !py-0"
                @click="openDiscord()"
              >
                {{ t('help_sidebar.report_issue.dialog.tips.discord.action') }}
              </RuiButton>
            </div>
          </div>

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
                @click="openPrivacyModeMenu()"
              >
                {{ t('help_sidebar.report_issue.dialog.tips.screenshot.action') }}
              </RuiButton>
              <span
                v-else
                class="text-xs text-rui-success flex items-center gap-1 py-1"
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
          @click="closeDialog()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
