import { get } from '@vueuse/core';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useProxyProtocol } from './use-proxy-protocol';

describe('useProxyProtocol', () => {
  describe('isProxy', () => {
    it('returns true when protocol starts with proxy:', () => {
      const protocol = ref<string>('proxy:makerdao:0x5e732C0954BFA46A7686b7fB1706C0fC4dfF4Ed7');
      const { isProxy } = useProxyProtocol(protocol);

      expect(get(isProxy)).toBe(true);
    });

    it('returns false when protocol does not start with proxy:', () => {
      const protocol = ref<string>('makerdao');
      const { isProxy } = useProxyProtocol(protocol);

      expect(get(isProxy)).toBe(false);
    });
  });

  describe('parsedProtocol', () => {
    it('returns the protocol name from a proxy protocol', () => {
      const protocol = ref<string>('proxy:makerdao:0x5e732C0954BFA46A7686b7fB1706C0fC4dfF4Ed7');
      const { parsedProtocol } = useProxyProtocol(protocol);

      expect(get(parsedProtocol)).toBe('makerdao');
    });

    it('returns the original value for non-proxy protocols', () => {
      const protocol = ref<string>('uniswap-v3');
      const { parsedProtocol } = useProxyProtocol(protocol);

      expect(get(parsedProtocol)).toBe('uniswap-v3');
    });

    it('returns the original value when proxy format is incomplete', () => {
      const protocol = ref<string>('proxy:');
      const { parsedProtocol } = useProxyProtocol(protocol);

      expect(get(parsedProtocol)).toBe('');
    });
  });

  describe('proxyAddress', () => {
    it('returns the address from a proxy protocol', () => {
      const protocol = ref<string>('proxy:makerdao:0x5e732C0954BFA46A7686b7fB1706C0fC4dfF4Ed7');
      const { proxyAddress } = useProxyProtocol(protocol);

      expect(get(proxyAddress)).toBe('0x5e732C0954BFA46A7686b7fB1706C0fC4dfF4Ed7');
    });

    it('returns undefined for non-proxy protocols', () => {
      const protocol = ref<string>('makerdao');
      const { proxyAddress } = useProxyProtocol(protocol);

      expect(get(proxyAddress)).toBeUndefined();
    });

    it('returns undefined when proxy format has no address', () => {
      const protocol = ref<string>('proxy:makerdao');
      const { proxyAddress } = useProxyProtocol(protocol);

      expect(get(proxyAddress)).toBeUndefined();
    });
  });

  describe('reactivity', () => {
    it('updates computed values when protocol changes', () => {
      const protocol = ref<string>('makerdao');
      const { isProxy, parsedProtocol, proxyAddress } = useProxyProtocol(protocol);

      expect(get(isProxy)).toBe(false);
      expect(get(parsedProtocol)).toBe('makerdao');
      expect(get(proxyAddress)).toBeUndefined();

      protocol.value = 'proxy:aave:0x5e732C0954BFA46A7686b7fB1706C0fC4dfF4Ed7';

      expect(get(isProxy)).toBe(true);
      expect(get(parsedProtocol)).toBe('aave');
      expect(get(proxyAddress)).toBe('0x5e732C0954BFA46A7686b7fB1706C0fC4dfF4Ed7');
    });
  });
});
