import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { PasswordStore } from './password-store';

describe('passwordStore', () => {
  let directory: string;
  let filePath: string;

  beforeEach(() => {
    directory = fs.mkdtempSync(path.join(os.tmpdir(), 'rotki-password-store-'));
    filePath = path.join(directory, 'config.json');
  });

  afterEach(() => {
    fs.rmSync(directory, { force: true, recursive: true });
  });

  function writeStore(contents: unknown): void {
    fs.writeFileSync(filePath, JSON.stringify(contents, undefined, '\t'), { encoding: 'utf8' });
  }

  it('should return undefined when no file exists', () => {
    expect(new PasswordStore(filePath).get('alice')).toBeUndefined();
    expect(new PasswordStore(filePath).isEmpty()).toBe(true);
  });

  it('should read an existing electron-store file', () => {
    writeStore({ alice: 'ciphertext' });
    expect(new PasswordStore(filePath).get('alice')).toBe('ciphertext');
  });

  it('should write the file in the format conf used', () => {
    new PasswordStore(filePath).set('alice', 'ciphertext');
    // Tab-indented, matching `JSON.stringify(value, undefined, '\t')`.
    expect(fs.readFileSync(filePath, { encoding: 'utf8' })).toBe('{\n\t"alice": "ciphertext"\n}');
  });

  it('should keep other entries when setting one', () => {
    writeStore({ alice: 'first', bob: 'second' });
    const store = new PasswordStore(filePath);
    store.set('alice', 'updated');

    expect(store.get('alice')).toBe('updated');
    expect(store.get('bob')).toBe('second');
  });

  it('should recover a dot-prop nested entry written by electron-store', () => {
    // conf's dot-prop `set` turned the username `john.doe` into nested objects, which every read
    // path then missed. The password was saved and could never be restored.
    writeStore({ john: { doe: 'ciphertext' } });

    expect(new PasswordStore(filePath).get('john.doe')).toBe('ciphertext');
  });

  it('should flatten a legacy nested entry back to disk', () => {
    writeStore({ john: { doe: 'ciphertext' } });
    new PasswordStore(filePath).get('john.doe');

    expect(JSON.parse(fs.readFileSync(filePath, { encoding: 'utf8' }))).toStrictEqual({
      'john.doe': 'ciphertext',
    });
  });

  it('should not rewrite a file that is already flat', () => {
    writeStore({ alice: 'ciphertext' });
    const before = fs.statSync(filePath).mtimeMs;

    new PasswordStore(filePath).get('alice');

    expect(fs.statSync(filePath).mtimeMs).toBe(before);
  });

  it('should write new entries flat even when the username has a dot', () => {
    const store = new PasswordStore(filePath);
    store.set('john.doe', 'ciphertext');

    expect(JSON.parse(fs.readFileSync(filePath, { encoding: 'utf8' }))).toStrictEqual({
      'john.doe': 'ciphertext',
    });
    expect(store.get('john.doe')).toBe('ciphertext');
  });

  it('should recover an entry nested more than one level deep', () => {
    writeStore({ a: { b: { c: 'ciphertext' } } });

    expect(new PasswordStore(filePath).get('a.b.c')).toBe('ciphertext');
  });

  it('should recover a nested entry without disturbing a flat neighbour', () => {
    writeStore({ alice: 'flat', john: { doe: 'nested' } });
    const store = new PasswordStore(filePath);

    expect(store.get('alice')).toBe('flat');
    expect(store.get('john.doe')).toBe('nested');
    expect(JSON.parse(fs.readFileSync(filePath, { encoding: 'utf8' }))).toStrictEqual({
      'alice': 'flat',
      'john.doe': 'nested',
    });
  });

  it('should keep a recovered entry when a later password is saved', () => {
    writeStore({ john: { doe: 'nested' } });
    const store = new PasswordStore(filePath);
    store.set('alice', 'ciphertext');

    expect(store.get('john.doe')).toBe('nested');
    expect(store.get('alice')).toBe('ciphertext');
  });

  it('should ignore values that are not passwords', () => {
    // Only strings are credentials. Anything else is not something this store wrote, and it is
    // dropped on the next write rather than being carried around.
    writeStore({ alice: 'ciphertext', count: 42, empty: null, list: ['a'] });
    const store = new PasswordStore(filePath);
    store.set('bob', 'second');

    expect(JSON.parse(fs.readFileSync(filePath, { encoding: 'utf8' }))).toStrictEqual({
      alice: 'ciphertext',
      bob: 'second',
    });
  });

  it('should create the directory when the user data path does not exist yet', () => {
    const nested = path.join(directory, 'missing', 'config.json');
    new PasswordStore(nested).set('alice', 'ciphertext');

    expect(new PasswordStore(nested).get('alice')).toBe('ciphertext');
  });

  it('should clear without a file present', () => {
    const store = new PasswordStore(filePath);
    store.clear();

    expect(store.isEmpty()).toBe(true);
  });

  it('should replace the file wholesale rather than merging into stale content', () => {
    writeStore({ alice: 'first', bob: 'second' });
    const store = new PasswordStore(filePath);
    store.clear();
    store.set('carol', 'third');

    expect(JSON.parse(fs.readFileSync(filePath, { encoding: 'utf8' }))).toStrictEqual({
      carol: 'third',
    });
  });

  it('should treat a corrupt file as empty rather than throwing', () => {
    fs.writeFileSync(filePath, 'not json', { encoding: 'utf8' });

    expect(new PasswordStore(filePath).get('alice')).toBeUndefined();
    expect(new PasswordStore(filePath).isEmpty()).toBe(true);
  });

  it('should clear every entry', () => {
    writeStore({ alice: 'first', bob: 'second' });
    const store = new PasswordStore(filePath);
    store.clear();

    expect(store.isEmpty()).toBe(true);
    expect(fs.readFileSync(filePath, { encoding: 'utf8' })).toBe('{}');
  });

  it('should leave no temporary file behind', () => {
    new PasswordStore(filePath).set('alice', 'ciphertext');

    expect(fs.readdirSync(directory)).toStrictEqual(['config.json']);
  });
});
