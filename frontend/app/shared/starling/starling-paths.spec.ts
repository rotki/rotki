import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { coreSearchDirectory, findCoreBinary } from './starling-paths';

describe('findCoreBinary', () => {
  let backend: string;
  let coreFolder: string;

  function place(...files: string[]): void {
    for (const file of files)
      fs.writeFileSync(path.join(coreFolder, file), '');
  }

  beforeEach(() => {
    backend = fs.mkdtempSync(path.join(os.tmpdir(), 'rotki-backend-'));
    coreFolder = path.join(backend, 'rotki-core');
    fs.mkdirSync(coreFolder);
  });

  afterEach(() => {
    fs.rmSync(backend, { force: true, recursive: true });
  });

  it.each([
    'rotki-core-1.44.1-linux',
    'rotki-core-1.44.1.dev503+gf63c0562a4.d20261006-windows.exe',
    'rotki-core-1.44.1-macos-arm64',
    'rotki-core-1.44.1-macos-x64',
  ])('should find a core named %s', (file) => {
    place(file);

    expect(findCoreBinary(backend)).toStrictEqual({ binary: path.join(coreFolder, file), dir: coreFolder });
  });

  it('should not take a renamed copy for the core, since Windows runs a full path whatever its extension', () => {
    place('rotki-core-1.44.1-windows.exe.bak');

    expect(findCoreBinary(backend)).toBeUndefined();
  });

  it('should pass over stray files beside the core instead of calling the folder ambiguous', () => {
    place('rotki-core-1.44.1-windows.exe', 'rotki-core-1.44.1-windows.exe.bak', 'rotki-core-notes.txt');

    expect(findCoreBinary(backend)?.binary).toBe(path.join(coreFolder, 'rotki-core-1.44.1-windows.exe'));
  });

  it('should still refuse two versions side by side', () => {
    place('rotki-core-1.44.1-linux', 'rotki-core-1.45.0-linux');

    expect(() => findCoreBinary(backend)).toThrow('Expected one rotki-core binary');
  });

  it('should look in the backend folder itself when there is no rotki-core folder', () => {
    fs.rmSync(coreFolder, { recursive: true });
    fs.writeFileSync(path.join(backend, 'rotki-core-1.44.1-linux'), '');

    expect(coreSearchDirectory(backend)).toBe(backend);
    expect(findCoreBinary(backend)?.binary).toBe(path.join(backend, 'rotki-core-1.44.1-linux'));
  });
});
