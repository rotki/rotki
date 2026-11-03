import type { BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';

const stubs = {
  IconMark: { props: ['src', 'alt'], template: '<img :src="src" :alt="alt" />' },
  LocationIcon: { props: ['item'], template: '<span :data-item="item" />' },
};

function manifest(connector: string, displayName: string, image: string | null): BankManifest {
  return { accessTier: '', authFlow: [], capabilities: [], connector, displayName, docsUrl: '', image, maintainer: '', secrets: [], setupNotes: [], version: '' };
}

function createWrapper(connector: string, bankCode?: string | null): VueWrapper<InstanceType<typeof BankConnectorIcon>> {
  return mount(BankConnectorIcon, { global: { stubs }, props: { bankCode, connector } });
}

describe('modules/banks/components/BankConnectorIcon', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useBankConnectionsStore().setManifests([manifest('qonto', 'Qonto', 'qonto.svg'), manifest('fints', 'FinTS/HBCI', null)]);
  });

  it('should show the logo a connector manifest names', () => {
    const logo = createWrapper('qonto').find('img');

    expect(logo.attributes('src')).toMatch(/\/protocols\/qonto\.svg$/);
    expect(logo.attributes('alt')).toBe('Qonto');
  });

  it('should show the bank icon for a connector without a logo, or one not loaded yet', () => {
    expect(createWrapper('fints').find('span').attributes('data-item')).toBe('banks');
    expect(createWrapper('unknown').find('img').exists()).toBe(false);
  });

  it('should show the logo of the bank its bank code names in the FinTS directory', () => {
    expect(createWrapper('fints', '12030000').find('img').attributes('src')).toMatch(/\/protocols\/bank_dkb\.svg$/);
  });

  it('should fall back to the connector for a bank code the directory has no logo for', () => {
    expect(createWrapper('fints', '10030400').find('span').attributes('data-item')).toBe('banks');
    expect(createWrapper('qonto', null).find('img').attributes('src')).toMatch(/\/protocols\/qonto\.svg$/);
  });
});
