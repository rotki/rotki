import type { RuleDraft } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const buildDraftMock = vi.fn<() => RuleDraft | undefined>();
const resetMock = vi.fn();
const canSave = ref<boolean>(true);
const kind = ref<'chain' | 'address'>('chain');
const scope = ref<'all' | 'specific'>('all');

vi.mock('@/modules/settings/general/disabled-chain-queries/use-rule-editor-form', () => ({
  useRuleEditorForm: vi.fn().mockReturnValue({
    address: ref<string | undefined>(undefined),
    addressOptions: computed(() => []),
    availableChainsForAddress: computed(() => []),
    buildDraft: (): RuleDraft | undefined => buildDraftMock(),
    canSave: computed<boolean>(() => get(canSave)),
    chainId: ref<string | undefined>(undefined),
    kind,
    reset: resetMock,
    scope,
    selectedChainIds: ref<string[]>([]),
  }),
}));

const DisabledChainQueryRuleDialog = (
  await import('@/modules/settings/general/disabled-chain-queries/DisabledChainQueryRuleDialog.vue')
).default;

async function mountDialog(props: {
  open?: boolean;
  editing?: { id: string; kind: 'chain'; chainId: string };
} = {}): Promise<VueWrapper> {
  setActivePinia(createPinia());
  const wrapper = mount(DisabledChainQueryRuleDialog, {
    attachTo: document.body,
    props: {
      editing: props.editing,
      open: props.open ?? true,
    },
    provide: libraryDefaults,
  });
  await flushPromises();
  await nextTick();
  return wrapper;
}

function findSaveButton(): HTMLButtonElement {
  const button = document.body.querySelector<HTMLButtonElement>('[data-testid="rule-save"]');
  if (!button)
    throw new Error('rule-save button not in DOM');
  return button;
}

describe('disabledChainQueryRuleDialog', () => {
  beforeEach(() => {
    buildDraftMock.mockReset();
    resetMock.mockReset();
    set(canSave, true);
    set(kind, 'chain');
    set(scope, 'all');
    document.body.innerHTML = '';
  });

  it('should call reset when the dialog opens', async () => {
    const wrapper = await mountDialog({ open: false });
    expect(resetMock).not.toHaveBeenCalled();
    await wrapper.setProps({ open: true });
    await flushPromises();
    expect(resetMock).toHaveBeenCalledOnce();
  });

  it('should emit save with the draft and undefined id when creating', async () => {
    buildDraftMock.mockReturnValue({ chainId: 'eth', kind: 'chain' });
    const wrapper = await mountDialog();
    findSaveButton().click();
    await flushPromises();
    expect(wrapper.emitted('save')).toEqual([
      [{ draft: { chainId: 'eth', kind: 'chain' }, id: undefined }],
    ]);
  });

  it('should emit save with the editing id when updating', async () => {
    buildDraftMock.mockReturnValue({ chainId: 'optimism', kind: 'chain' });
    const wrapper = await mountDialog({
      editing: { chainId: 'eth', id: 'rule-7', kind: 'chain' },
    });
    findSaveButton().click();
    await flushPromises();
    expect(wrapper.emitted('save')).toEqual([
      [{ draft: { chainId: 'optimism', kind: 'chain' }, id: 'rule-7' }],
    ]);
  });

  it('should close itself after a successful save', async () => {
    buildDraftMock.mockReturnValue({ chainId: 'eth', kind: 'chain' });
    const wrapper = await mountDialog();
    findSaveButton().click();
    await flushPromises();
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false]);
  });

  it('should not emit save when buildDraft returns undefined', async () => {
    buildDraftMock.mockReturnValue(undefined);
    const wrapper = await mountDialog();
    const button = findSaveButton();
    button.click();
    await flushPromises();
    expect(wrapper.emitted('save')).toBeUndefined();
  });

  it('should disable the save button while the form is invalid', async () => {
    set(canSave, false);
    await mountDialog();
    expect(findSaveButton().disabled).toBe(true);
  });
});
