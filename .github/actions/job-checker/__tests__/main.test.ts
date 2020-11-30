import {changeDetected} from '../src/action'

test('a file matches', () => {
  const monitored = ['rotkehlchen', 'requirements.txt']
  const changed = ['requirements.txt']
  expect(changeDetected(monitored, changed)).toBe(true)
})

test('a path matches', () => {
  const monitored = ['rotkehlchen', 'requirements.txt']
  const changed = ['rotkehlchen/args.py']
  expect(changeDetected(monitored, changed)).toBe(true)
})

test('nothing matches', () => {
  const monitored = ['rotkehlchen', 'requirements.txt']
  const changed = ['docs']
  expect(changeDetected(monitored, changed)).toBe(false)
})
