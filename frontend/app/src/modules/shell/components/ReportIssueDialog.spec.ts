import { SUPPORT_EMAIL } from '@shared/external-links';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick, type Ref } from 'vue';
import ReportIssueDialog from '@/modules/shell/components/ReportIssueDialog.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { close, copy, initialDescription, initialTitle, openUrl, privacyMode, scrambleEnabled, showPrivacyModeMenu, visible } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    close: vi.fn(),
    copy: vi.fn(),
    initialDescription: ref<string>(''),
    initialTitle: ref<string>(''),
    openUrl: vi.fn(),
    privacyMode: ref<number>(0),
    scrambleEnabled: ref<boolean>(false),
    showPrivacyModeMenu: ref<boolean>(false),
    visible: ref<boolean>(true),
  };
});

vi.mock('@/modules/core/common/use-report-issue', () => ({
  useReportIssue: (): Record<string, unknown> => ({
    close,
    initialDescription,
    initialTitle,
    visible,
  }),
}));

vi.mock('@/modules/core/common/use-area-visibility-store', () => ({
  useAreaVisibilityStore: (): { showPrivacyModeMenu: Ref<boolean> } => ({ showPrivacyModeMenu }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { openUrl: Mock } => ({ openUrl }),
}));

vi.mock('@/modules/settings/use-scramble-settings', () => ({
  useScrambleSetting: (): { enabled: Ref<boolean> } => ({ enabled: scrambleEnabled }),
}));

vi.mock('@/modules/settings/use-privacy', () => ({
  usePrivacyMode: (): { privacyMode: Ref<number> } => ({ privacyMode }),
}));

vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');
  return { ...actual, useClipboard: (): { copy: Mock } => ({ copy }) };
});

const EmailButtonStub = {
  emits: ['submit-email', 'copy-email', 'open-gmail'],
  name: 'ReportIssueEmailButton',
  props: ['email', 'isFormValid'],
  template: `<div>
    <button data-testid="stub-mailto" @click="$emit('submit-email')" />
    <button data-testid="stub-copy" @click="$emit('copy-email')" />
    <button data-testid="stub-gmail" @click="$emit('open-gmail')" />
  </div>`,
};

/** `RuiDialog` teleports, so a pass-through keeps the card inside the wrapper. */
const DialogStub = { name: 'RuiDialog', props: ['modelValue'], template: '<div><slot /></div>' };

function createWrapper(): VueWrapper<any> {
  return mount(ReportIssueDialog, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        ReportIssueDiscordTip: { emits: ['open-discord'], name: 'ReportIssueDiscordTip', template: '<button data-testid="stub-discord" @click="$emit(\'open-discord\')" />' },
        ReportIssueEmailButton: EmailButtonStub,
        RuiDialog: DialogStub,
      },
    },
  });
}

/** Fills the form the way the user does, through the two fields the dialog binds. */
async function fillDraft(wrapper: VueWrapper<any>, title = 'a title', description = 'a description'): Promise<void> {
  await wrapper.findComponent({ name: 'RuiTextField' }).vm.$emit('update:modelValue', title);
  await wrapper.findComponent({ name: 'RuiTextArea' }).vm.$emit('update:modelValue', description);
}

describe('reportIssueDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(initialTitle, '');
    set(initialDescription, '');
    set(privacyMode, 0);
    set(scrambleEnabled, false);
    set(showPrivacyModeMenu, false);
  });

  /** The dialog can be opened with a subject already chosen, from wherever asked for it. */
  it('should open on the draft the caller asked for', async () => {
    set(initialTitle, 'a crash on login');
    set(initialDescription, 'it happened twice');

    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.findComponent({ name: 'RuiTextField' }).props('modelValue')).toBe('a crash on login');
    expect(wrapper.findComponent({ name: 'RuiTextArea' }).props('modelValue')).toBe('it happened twice');
  });

  describe('submitting', () => {
    it('should refuse every route until the form is filled', () => {
      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=report-issue-github]').attributes('disabled')).toBeDefined();
      expect(wrapper.find('[data-testid=report-issue-google-form]').attributes('disabled')).toBeDefined();
      expect(wrapper.findComponent(EmailButtonStub).props('isFormValid')).toBe(false);
    });

    it('should offer every route once it is', async () => {
      const wrapper = createWrapper();

      await fillDraft(wrapper);

      expect(wrapper.find('[data-testid=report-issue-github]').attributes('disabled')).toBeUndefined();
      expect(wrapper.findComponent(EmailButtonStub).props('isFormValid')).toBe(true);
    });

    it('should carry the draft to github', async () => {
      const wrapper = createWrapper();
      await fillDraft(wrapper, 'a crash', 'it happened twice');

      await wrapper.find('[data-testid=report-issue-github]').trigger('click');

      expect(openUrl).toHaveBeenCalledWith(expect.stringContaining('a%20crash'));
      expect(openUrl).toHaveBeenCalledWith(expect.stringContaining('github.com'));
    });

    it('should carry the draft to the google form', async () => {
      const wrapper = createWrapper();
      await fillDraft(wrapper, 'a crash');

      await wrapper.find('[data-testid=report-issue-google-form]').trigger('click');

      expect(openUrl).toHaveBeenCalledWith(expect.stringContaining('a%20crash'));
    });

    it('should carry the draft to a mail client', async () => {
      const wrapper = createWrapper();
      await fillDraft(wrapper, 'a crash');

      await wrapper.find('[data-testid=stub-mailto]').trigger('click');

      expect(openUrl).toHaveBeenCalledWith(expect.stringContaining('mailto:'));
    });

    it('should carry the draft to gmail', async () => {
      const wrapper = createWrapper();
      await fillDraft(wrapper, 'a crash');

      await wrapper.find('[data-testid=stub-gmail]').trigger('click');

      expect(openUrl).toHaveBeenCalledWith(expect.stringContaining('mail.google.com'));
    });

    /** The report continues in the browser, so the dialog has nothing left to do. */
    it('should close once a route was taken', async () => {
      const wrapper = createWrapper();
      await fillDraft(wrapper);

      await wrapper.find('[data-testid=report-issue-github]').trigger('click');

      expect(close).toHaveBeenCalledTimes(1);
    });

    /** Reopening starts a fresh report rather than the last one the user walked away from. */
    it('should forget the draft on close', async () => {
      const wrapper = createWrapper();
      await fillDraft(wrapper, 'a crash');

      await wrapper.find('[data-testid=report-issue-close]').trigger('click');

      expect(wrapper.findComponent({ name: 'RuiTextField' }).props('modelValue')).toBe('');
      expect(wrapper.findComponent({ name: 'RuiTextArea' }).props('modelValue')).toBe('');
    });
  });

  describe('the support address', () => {
    it('should be offered for copying', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=stub-copy]').trigger('click');

      expect(copy).toHaveBeenCalledWith(SUPPORT_EMAIL);
    });

    it('should be handed to the button as the address to show', () => {
      expect(createWrapper().findComponent(EmailButtonStub).props('email')).toBe(SUPPORT_EMAIL);
    });
  });

  /** Discord is a conversation rather than a filed report, so the dialog stays up behind it. */
  it('should stay open when discord is opened', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=stub-discord]').trigger('click');

    expect(openUrl).toHaveBeenCalledTimes(1);
    expect(close).not.toHaveBeenCalled();
  });

  /**
   * The tip exists to stop a screenshot leaking balances, so it offers the privacy menu only while
   * nothing is masking them yet, and otherwise reports what is already on.
   */
  describe('the screenshot privacy tip', () => {
    it('should offer the privacy menu while nothing is masked', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=report-issue-enable-privacy]').trigger('click');

      expect(get(showPrivacyModeMenu)).toBe(true);
      expect(close).toHaveBeenCalledTimes(1);
    });

    it('should stop offering it once privacy mode is on', () => {
      set(privacyMode, 1);

      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=report-issue-enable-privacy]').exists()).toBe(false);
    });

    it('should stop offering it once scrambling is on', () => {
      set(scrambleEnabled, true);

      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=report-issue-enable-privacy]').exists()).toBe(false);
    });

    it('should name semi-private mode', () => {
      set(privacyMode, 1);

      expect(createWrapper().find('[data-testid=report-issue-privacy-status]').text())
        .toContain('semi_private');
    });

    it('should name private mode', () => {
      set(privacyMode, 2);

      expect(createWrapper().find('[data-testid=report-issue-privacy-status]').text())
        .toContain('tips.screenshot.private');
    });

    it('should name both when scrambling joins a privacy mode', () => {
      set(privacyMode, 2);
      set(scrambleEnabled, true);

      const status = createWrapper().find('[data-testid=report-issue-privacy-status]').text();

      expect(status).toContain('tips.screenshot.private');
      expect(status).toContain('scramble');
    });
  });
});
