import type { ComponentPublicInstance } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { ActionStatus } from '@/modules/core/common/action';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

interface MergePayload {
  sourceIdentifier: string;
  targetIdentifier: string;
}

const mergeAssets = vi.fn<(payload: MergePayload) => Promise<ActionStatus<string | ValidationErrors>>>();

vi.mock('@/modules/assets/use-assets', () => ({
  useAssets: vi.fn().mockImplementation(() => ({ mergeAssets })),
}));

const MergeDialog = (await import('@/modules/assets/admin/MergeDialog.vue')).default;

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'update:asset', 'blur', 'focus'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'excludes'],
    template: '<div />',
  };
}

describe('mergeDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof MergeDialog>>;

  beforeEach(() => {
    vi.clearAllMocks();
    mergeAssets.mockResolvedValue({ success: true });
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof MergeDialog>> {
    return mount(MergeDialog, {
      global: {
        stubs: {
          AssetSelect: inputStub('AssetSelect'),
          RuiCard: {
            name: 'RuiCard',
            template: '<div><slot name="header" /><slot name="subheader" /><slot /><slot name="footer" /></div>',
          },
          RuiDialog: {
            name: 'RuiDialog',
            props: ['modelValue'],
            template: '<div><slot v-if="modelValue" /></div>',
          },
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: { modelValue: true, ...props },
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  function submitDisabled(): unknown {
    return wrapper.findComponent<StubInstance>('[data-testid=merge-submit]').props('disabled');
  }

  async function edit(testId: string, value: string): Promise<void> {
    const input = field(testId);
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  async function fillBoth(): Promise<void> {
    await edit('merge-source', 'eip155:1/erc20:0xsource');
    await edit('merge-target', 'ETH');
  }

  async function submit(): Promise<void> {
    await wrapper.find('form').trigger('submit');
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should show no message before anything is touched', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('merge-source')).toEqual([]);
    expect(messages('merge-target')).toEqual([]);
  });

  it('should block the merge while both identifiers are empty', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(submitDisabled()).toBe(true);
  });

  it('should block the merge while only the source is filled', async () => {
    wrapper = createWrapper();
    await edit('merge-source', 'eip155:1/erc20:0xsource');

    expect(submitDisabled()).toBe(true);
  });

  it('should block the merge while only the target is filled', async () => {
    wrapper = createWrapper();
    await edit('merge-target', 'ETH');

    expect(submitDisabled()).toBe(true);
  });

  it('should allow the merge once both identifiers are filled', async () => {
    wrapper = createWrapper();
    await fillBoth();

    expect(submitDisabled()).toBe(false);
    // Both fields stay editable while nothing is in flight.
    expect(field('merge-source').props('disabled')).toBe(false);
    expect(field('merge-target').props('disabled')).toBe(false);
  });

  it('should keep the merge blocked for whitespace-only identifiers', async () => {
    wrapper = createWrapper();
    await edit('merge-source', '   ');
    await edit('merge-target', '   ');

    expect(submitDisabled()).toBe(true);
  });

  it('should report the source message while typing, before the field is left', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    // No blur: the submit button is gated on validity, and a disabled button cannot be clicked to
    // blur the field, so waiting for blur would leave the user with no message at all.
    field('merge-source').vm.$emit('update:modelValue', '');
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('merge-source')).toEqual(['merge_dialog.source.non_empty']);
  });

  it('should report the source message once it is emptied', async () => {
    wrapper = createWrapper();
    await fillBoth();

    await edit('merge-source', '');

    expect(messages('merge-source')).toEqual(['merge_dialog.source.non_empty']);
    expect(messages('merge-target')).toEqual([]);
  });

  it('should report the target message once it is emptied', async () => {
    wrapper = createWrapper();
    await fillBoth();

    await edit('merge-target', '');

    expect(messages('merge-target')).toEqual(['merge_dialog.target.non_empty']);
  });

  it('should seed both fields from the props when the dialog opens', async () => {
    wrapper = createWrapper({
      modelValue: false,
      sourceIdentifier: 'eip155:1/erc20:0xseeded',
      targetIdentifier: 'BTC',
    });
    await wrapper.setProps({ modelValue: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('merge-source').props('modelValue')).toBe('eip155:1/erc20:0xseeded');
    expect(field('merge-target').props('modelValue')).toBe('BTC');
  });

  it('should merge the two identifiers and announce the result', async () => {
    wrapper = createWrapper();
    await fillBoth();

    await submit();

    expect(mergeAssets).toHaveBeenCalledWith({
      sourceIdentifier: 'eip155:1/erc20:0xsource',
      targetIdentifier: 'ETH',
    });
    expect(wrapper.emitted<[MergePayload]>('merged')?.at(-1)).toEqual([{
      sourceIdentifier: 'eip155:1/erc20:0xsource',
      targetIdentifier: 'ETH',
    }]);
  });

  it('should clear both fields after a successful merge', async () => {
    wrapper = createWrapper();
    await fillBoth();

    await submit();

    expect(field('merge-source').props('modelValue')).toBe('');
    expect(field('merge-target').props('modelValue')).toBe('');
  });

  it('should show a plain failure message under the source field', async () => {
    mergeAssets.mockResolvedValue({ message: 'assets are not compatible', success: false });
    wrapper = createWrapper();
    await fillBoth();

    await submit();

    expect(messages('merge-source')).toEqual(['assets are not compatible']);
  });

  it('should fan a per-field failure onto the field it names', async () => {
    mergeAssets.mockResolvedValue({
      message: { targetIdentifier: ['unknown asset'] } satisfies ValidationErrors,
      success: false,
    });
    wrapper = createWrapper();
    await fillBoth();

    await submit();

    expect(messages('merge-target')).toEqual(['unknown asset']);
  });

  it('should keep the merge blocked while a server error stands', async () => {
    mergeAssets.mockResolvedValue({ message: 'assets are not compatible', success: false });
    wrapper = createWrapper();
    await fillBoth();

    await submit();

    expect(submitDisabled()).toBe(true);
  });

  it('should drop the server message when the field is focused again', async () => {
    mergeAssets.mockResolvedValue({ message: 'assets are not compatible', success: false });
    wrapper = createWrapper();
    await fillBoth();
    await submit();

    field('merge-source').vm.$emit('focus');
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('merge-source')).toEqual([]);
  });

  it('should clear the fields when the dialog closes', async () => {
    wrapper = createWrapper();
    await fillBoth();

    await wrapper.setProps({ modelValue: false });
    await vi.advanceTimersByTimeAsync(200);
    await wrapper.setProps({ modelValue: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('merge-source').props('modelValue')).toBe('');
    expect(field('merge-target').props('modelValue')).toBe('');
  });
});
