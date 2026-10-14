import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import NftImageRenderingSetting from '@/modules/settings/general/nft/NftImageRenderingSetting.vue';
import { createRuiPlugin } from '@/plugins/rui';

const {
  renderAllModel,
  renderWriteError,
  renderWriteSuccess,
  whitelistModel,
  whitelistWriteError,
  whitelistWriteSuccess,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');

  return {
    renderAllModel: ref<boolean>(false),
    renderWriteError: ref<string>(''),
    renderWriteSuccess: ref<boolean>(false),
    whitelistModel: ref<string[]>([]),
    whitelistWriteError: ref<string>(''),
    whitelistWriteSuccess: ref<boolean>(false),
  };
});

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
      expect(wrapper.find('[data-testid=nft-allow-all-confirmation]').exists()).toBe(false);
    });
  });

  /**
   * Rendering every NFT image fetches from arbitrary domains, so it is confirmed inline rather than
   * applied on the click.
   */
  describe('allowing every domain', () => {
    it('should ask before applying it', async () => {
      const wrapper = createWrapper();

      await chooseMode(wrapper, 'all');

      expect(get(renderAllModel)).toBe(false);
      expect(wrapper.find('[data-testid=nft-allow-all-confirmation]').exists()).toBe(true);
    });

    it('should apply it once confirmed', async () => {
      const wrapper = createWrapper();
      await chooseMode(wrapper, 'all');

      await wrapper.find('[data-testid=nft-allow-all-confirm]').trigger('click');

      expect(get(renderAllModel)).toBe(true);
      expect(wrapper.find('[data-testid=nft-allow-all-confirmation]').exists()).toBe(false);
    });

    /** Leaving the radio on `all` after a refusal would misreport what is persisted. */
    it('should put the control back when refused', async () => {
      const wrapper = createWrapper();
      await chooseMode(wrapper, 'all');

      await wrapper.find('[data-testid=nft-allow-all-cancel]').trigger('click');

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

    it('should name only the new domains before adding them', async () => {
      set(whitelistModel, ['existing.com']);
      const wrapper = createWrapper();
      await type(wrapper, 'existing.com,rotki.com');

      await saveButton(wrapper).trigger('click');

      const confirmation = wrapper.find('[data-testid=nft-whitelist-confirmation]');
      expect(confirmation.text()).toContain('rotki.com');
      expect(confirmation.text()).not.toContain('existing.com');
      expect(get(whitelistModel)).toEqual(['existing.com']);
    });

    it('should add the entered domains to the stored list once confirmed', async () => {
      set(whitelistModel, ['existing.com']);
      const wrapper = createWrapper();
      await type(wrapper, 'rotki.com');
      await saveButton(wrapper).trigger('click');

      await wrapper.find('[data-testid=nft-whitelist-confirm]').trigger('click');

      expect(get(whitelistModel)).toEqual(['existing.com', 'rotki.com']);
    });

    it('should keep the list untouched when the add is cancelled', async () => {
      set(whitelistModel, ['existing.com']);
      const wrapper = createWrapper();
      await type(wrapper, 'rotki.com');
      await saveButton(wrapper).trigger('click');

      await wrapper.find('[data-testid=nft-whitelist-cancel]').trigger('click');

      expect(get(whitelistModel)).toEqual(['existing.com']);
      expect(wrapper.find('[data-testid=nft-whitelist-confirmation]').exists()).toBe(false);
    });

    it('should say when no domain is whitelisted yet', () => {
      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=nft-whitelist-empty]').exists()).toBe(true);
    });

    it('should drop a domain the user removes', async () => {
      set(whitelistModel, ['keep.com', 'drop.com']);
      const wrapper = createWrapper();

      await wrapper.findAllComponents({ name: 'RuiChip' })[1].vm.$emit('click:close');
      await nextTick();

      expect(get(whitelistModel)).toEqual(['keep.com']);
    });

    /** The whitelist has no effect while every domain is allowed, so it is not shown. */
    it('should be hidden while every domain is allowed', async () => {
      set(whitelistModel, ['keep.com']);
      set(renderAllModel, true);
      const wrapper = createWrapper();
      await nextTick();

      expect(wrapper.find('[data-testid=nft-whitelist]').exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'RuiTextField' }).exists()).toBe(false);
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
});
