import { describe, expect, it } from 'vitest';
import { getMimeType } from './create-protocol';

describe('getMimeType', () => {
  it.each([
    ['app.js', 'application/javascript'],
    ['index.html', 'text/html'],
    ['styles.css', 'text/css'],
    ['icon.svg', 'image/svg+xml'],
    ['icon.svgz', 'image/svg+xml'],
    ['logo.png', 'image/png'],
    ['photo.jpg', 'image/jpeg'],
    ['photo.jpeg', 'image/jpeg'],
    ['data.json', 'application/json'],
    ['module.wasm', 'application/wasm'],
  ])('should map %s to %s', (fileName, expected) => {
    expect(getMimeType(fileName)).toBe(expected);
  });

  it('should fall back to application/octet-stream for unknown extensions', () => {
    expect(getMimeType('archive.zip')).toBe('application/octet-stream');
  });

  it('should fall back to application/octet-stream when there is no extension', () => {
    expect(getMimeType('LICENSE')).toBe('application/octet-stream');
  });

  it('should match extensions case-insensitively', () => {
    expect(getMimeType('APP.JS')).toBe('application/javascript');
    expect(getMimeType('Photo.JPEG')).toBe('image/jpeg');
  });

  it('should resolve the extension from a full path', () => {
    expect(getMimeType('/some/nested/dir/app.css')).toBe('text/css');
  });
});
