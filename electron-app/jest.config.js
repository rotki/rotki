module.exports = {
  preset: '@vue/cli-plugin-unit-jest/presets/typescript-and-babel',
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{ts,vue}',
    '!**/node_modules/**',
    '!**/vendor/**'
  ],
  coverageReporters: ['html', 'lcov', 'text', 'text-summary'],
  reporters: ['default', ['jest-junit', { outputDirectory: 'coverage' }]]
};
