import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import NftImageRenderingSetting from '@/modules/settings/general/nft/NftImageRenderingSetting.vue';
import { createRuiPlugin } from '@/plugins/rui';

const {
  confirm,
  confirmVisible,
  renderAllModel,
  renderWriteError,
  renderWriteSuccess,
  whitelistModel,
  whitelistWriteError,
  whitelistWriteSuccess,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  /** Holds what the confirmation store was handed, so a test can accept or dismiss the prompt. */
  const confirm: { accept?: () => void; reject?: () => void } = {};

  return {
    confirm,
    confirmVisible: ref<boolean>(false),
    renderAllModel: ref<boolean>(false),
    renderWriteError: ref<string>(''),
    renderWriteSuccess: ref<boolean>(false),
    whitelistModel: ref<string[]>([]),
    whitelistWriteError: ref<string>(''),
    whitelistWriteSuccess: ref<boolean>(false),
  };
});

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({
    show: (_message: unknown, accept: () => void, reject?: () => void): void => {
      confirm.accept = accept;
      confirm.reject = reject;
    },
    visible: confirmVisible,
  }),
}));

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: (key: string): Record<string, unknown> =>
    key === 'renderAllNftImages'
      ? { error: renderWriteError, model: renderAllModel, success: renderWriteSuccess }
      : { error: whitelistWriteError, model: whitelistModel, success: whitelistWriteSuccess },
}));

function createWrapper(): VueWrapper<any> {
  return mount(NftImageRenderingSetting, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        ConfirmDialog: {
          emits: ['confirm', 'cancel'],
          name: 'ConfirmDialog',
          props: ['display', 'title', 'message', 'maxWidth'],
          template: `<div>
            <slot />
            <button data-testid="stub-confirm" @click="$emit('confirm')" />
            <button data-testid="stub-cancel" @click="$emit('cancel')" />
          </div>`,
        },
      },
    },
  });
}

function radio(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent({ name: 'RuiRadioGroup' });
}

/** Picks a rendering mode the way the radio group reports it. */
async function chooseMode(wrapper: VueWrapper<any>, mode: 'all' | 'whitelisted'): Promise<void> {
  await radio(wrapper).vm.$emit('update:modelValue', mode);
  await nextTick();
}

describe('nftImageRenderingSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirm.accept = undefined;
    confirm.reject = undefined;
    set(confirmVisible, false);
    set(renderAllModel, false);
    set(renderWriteError, '');
    set(renderWriteSuccess, false);
    set(whitelistModel, []);
    set(whitelistWriteError, '');
    set(whitelistWriteSuccess, false);
  });

  describe('the rendering mode', () => {
    it('should open on the persisted setting', () => {
      set(renderAllModel, true);

      expect(radio(createWrapper()).props('modelValue')).toBe('all');
    });

    it('should follow the setting changing elsewhere', async () => {
      const wrapper = createWrapper();

      set(renderAllModel, true);
      await nextTick();

      expect(radio(wrapper).props('modelValue')).toBe('all');
    });

    it('should restrict to the whitelist without asking', async () => {
      set(renderAllModel, true);
      const wrapper = createWrapper();

      await chooseMode(wrapper, 'whitelisted');

      expect(get(renderAllModel)).toBe(false);
      expect(confirm.accept).toBeUndefined();
    });
  });

  /**
   * Rendering every NFT image fetches from arbitrary domains, so it is confirmed rather than
   * applied on the click.
   */
  describe('allowing every domain', () => {
    it('should ask before applying it', async () => {
      const wrapper = createWrapper();

      await chooseMode(wrapper, 'all');

      expect(get(renderAllModel)).toBe(false);
      expect(confirm.accept).toBeDefined();
    });

    it('should apply it once confirmed', async () => {
      const wrapper = createWrapper();
      await chooseMode(wrapper, 'all');

      confirm.accept?.();
      await nextTick();

      expect(get(renderAllModel)).toBe(true);
    });

    /** Leaving the radio on `all` after a refusal would misreport what is persisted. */
    it('should put the control back when refused', async () => {
      const wrapper = createWrapper();
      await chooseMode(wrapper, 'all');

      confirm.reject?.();
      await nextTick();

      expect(radio(wrapper).props('modelValue')).toBe('whitelisted');
      expect(get(renderAllModel)).toBe(false);
    });
  });

  describe('the whitelist', () => {
    async function type(wrapper: VueWrapper<any>, value: string): Promise<void> {
      await wrapper.findComponent({ name: 'RuiTextField' }).vm.$emit('update:modelValue', value);
      await nextTick();
    }

    function saveButton(wrapper: VueWrapper<any>): ReturnType<VueWrapper<any>['find']> {
      return wrapper.find('[data-testid=nft-whitelist-save]');
    }

    it('should refuse to save nothing', () => {
      expect(saveButton(createWrapper()).attributes('disabled')).toBeDefined();
    });

    it('should offer to save once a domain is entered', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'rotki.com');

      expect(saveButton(wrapper).attributes('disabled')).toBeUndefined();
    });

    it('should add the entered domains to the stored list', async () => {
      set(whitelistModel, ['existing.com']);
      const wrapper = createWrapper();
      await type(wrapper, 'rotki.com');

      await wrapper.find('[data-testid=stub-confirm]').trigger('click');

      expect(get(whitelistModel)).toEqual(['existing.com', 'rotki.com']);
    });

    it('should keep the list untouched when the save is dismissed', async () => {
      set(whitelistModel, ['existing.com']);
      const wrapper = createWrapper();
      await type(wrapper, 'rotki.com');

      await wrapper.find('[data-testid=stub-cancel]').trigger('click');

      expect(get(whitelistModel)).toEqual(['existing.com']);
    });

    it('should count what was entered', async () => {
      const wrapper = createWrapper();

      await type(wrapper, 'rotki.com,example.com');

      expect(wrapper.text()).toContain('whitelisted_domain_entries::2');
    });

    it('should drop a domain the user removes', async () => {
      set(whitelistModel, ['keep.com', 'drop.com']);
      const wrapper = createWrapper();

      await wrapper.findAllComponents({ name: 'RuiChip' })[1].vm.$emit('click:close');
      await nextTick();

      expect(get(whitelistModel)).toEqual(['keep.com']);
    });

    /** The whitelist has no effect while every domain is allowed, so it is not offered. */
    it('should be closed for editing while every domain is allowed', async () => {
      set(whitelistModel, ['keep.com']);
      set(renderAllModel, true);
      const wrapper = createWrapper();
      await nextTick();

      expect(wrapper.findComponent({ name: 'RuiTextField' }).props('disabled')).toBe(true);
      expect(wrapper.findComponent({ name: 'RuiChip' }).props('closeable')).toBe(false);
    });
  });

  /** The entered domains have moved into the stored list, so leaving them typed invites a re-add. */
  describe('after the whitelist is written', () => {
    async function typeAndSettle(wrapper: VueWrapper<any>, saved: boolean): Promise<void> {
      await wrapper.findComponent({ name: 'RuiTextField' }).vm.$emit('update:modelValue', 'rotki.com');
      await nextTick();
      set(whitelistWriteSuccess, saved);
      await nextTick();
    }

    it('should clear the input once the write lands', async () => {
      const wrapper = createWrapper();

      await typeAndSettle(wrapper, true);

      expect(wrapper.findComponent({ name: 'RuiTextField' }).props('modelValue')).toBe('');
    });

    it('should leave what was typed while nothing has landed', async () => {
      const wrapper = createWrapper();

      await typeAndSettle(wrapper, false);

      expect(wrapper.findComponent({ name: 'RuiTextField' }).props('modelValue')).toBe('rotki.com');
    });

    it('should surface what the write failed with', async () => {
      const wrapper = createWrapper();

      set(whitelistWriteError, 'the backend said no');
      await nextTick();

      expect(wrapper.findComponent({ name: 'RuiTextField' }).props('errorMessages'))
        .toContain('general_settings.nft_setting.messages.error: the backend said no');
    });
  });

  /** The page above dims while either prompt is up, so it needs telling. */
  describe('telling the page a dialog is open', () => {
    it('should report the save confirmation opening', async () => {
      const wrapper = createWrapper();
      await wrapper.findComponent({ name: 'RuiTextField' }).vm.$emit('update:modelValue', 'rotki.com');
      await nextTick();

      await wrapper.find('[data-testid=nft-whitelist-save]').trigger('click');

      expect(wrapper.emitted<[boolean]>('dialog-open')?.at(-1)?.[0]).toBe(true);
    });

    it('should report the mode confirmation opening', async () => {
      const wrapper = createWrapper();

      set(confirmVisible, true);
      await nextTick();

      expect(wrapper.emitted<[boolean]>('dialog-open')?.at(-1)?.[0]).toBe(true);
    });

    it('should report both closing again', async () => {
      const wrapper = createWrapper();
      set(confirmVisible, true);
      await nextTick();

      set(confirmVisible, false);
      await nextTick();

      expect(wrapper.emitted<[boolean]>('dialog-open')?.at(-1)?.[0]).toBe(false);
    });
  });
});
