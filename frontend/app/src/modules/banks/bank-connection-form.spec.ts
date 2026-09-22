import type { BankFormData, BankManifest } from '@/modules/banks/types';
import { describe, expect, it } from 'vitest';
import {
  bankConnectionSchema,
  emptyCredentials,
  toBankConnectionFormState,
} from '@/modules/banks/bank-connection-form';

const manifest: BankManifest = {
  accessTier: 'official api',
  authFlow: [{ primitive: 'static secret' }],
  capabilities: ['balances', 'transactions'],
  connectorIdentifier: 'qonto',
  displayName: 'Qonto',
  docsUrl: 'https://docs.qonto.com',
  fixedLocation: 'qonto',
  maintainer: 'rotki',
  secrets: [
    { description: 'login', label: 'Login', secret: false, slot: 'api_key' },
    { description: 'secret', label: 'Secret key', secret: true, slot: 'api_secret' },
  ],
  setupNotes: ['note'],
  version: '1.0.0',
};

const fints: BankManifest = { ...manifest, connectorIdentifier: 'fints', displayName: 'FinTS', fixedLocation: null };

function issuesOf(mode: BankFormData['mode'], state: Record<string, unknown>, of: BankManifest = manifest): string[] {
  const result = bankConnectionSchema(mode, of).safeParse(state);
  return result.success ? [] : result.error.issues.map(issue => issue.path.join('.'));
}

describe('bankConnectionSchema', () => {
  it('should demand a name and every manifest credential when adding', () => {
    expect(issuesOf('add', {
      connector: 'qonto',
      credentials: { api_key: '', api_secret: ' ' },
      location: 'qonto',
      name: '',
      newName: '',
    })).toEqual(['name', 'credentials.api_key', 'credentials.api_secret']);
  });

  it('should accept a complete add form', () => {
    expect(issuesOf('add', {
      connector: 'qonto',
      credentials: { api_key: 'login', api_secret: 'secret' },
      location: 'qonto',
      name: 'Qonto main',
      newName: '',
    })).toEqual([]);
  });

  it('should only demand the new name when editing, credentials stay optional', () => {
    expect(issuesOf('edit', {
      connector: 'qonto',
      credentials: { api_key: '', api_secret: '' },
      location: 'qonto',
      name: 'Qonto main',
      newName: '',
    })).toEqual(['newName']);
    expect(issuesOf('edit', {
      connector: 'qonto',
      credentials: { api_key: '', api_secret: '' },
      location: 'qonto',
      name: 'Qonto main',
      newName: 'Qonto renamed',
    })).toEqual([]);
  });

  it('should demand a connector when adding without one', () => {
    expect(issuesOf('add', {
      connector: '',
      credentials: { api_key: 'login', api_secret: 'secret' },
      location: '',
      name: 'x',
      newName: '',
    })).toEqual(['connector']);
  });

  it('should demand a bank location only from a connector that does not fix it', () => {
    const state = { connector: 'fints', credentials: { api_key: 'login', api_secret: 'secret' }, location: '', name: 'x', newName: '' };
    expect(issuesOf('add', state, fints)).toEqual(['location']);
    expect(issuesOf('add', { ...state, location: 'custom:ing' }, fints)).toEqual([]);
    expect(issuesOf('add', state)).toEqual([]);
  });
});

describe('emptyCredentials', () => {
  it('should create one empty entry per manifest slot', () => {
    expect(emptyCredentials(manifest)).toEqual({ api_key: '', api_secret: '' });
    expect(emptyCredentials(undefined)).toEqual({});
  });
});

describe('toBankConnectionFormState', () => {
  it('should copy the credentials so edits do not leak into the model before save', () => {
    const data: BankFormData = {
      connector: 'qonto',
      credentials: { api_key: 'a', api_secret: 'b' },
      location: 'qonto',
      mode: 'add',
      name: 'n',
      newName: '',
    };
    const state = toBankConnectionFormState(data);
    state.credentials.api_key = 'changed';
    expect(data.credentials.api_key).toBe('a');
  });
});
