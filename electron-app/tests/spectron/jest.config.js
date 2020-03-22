module.exports = {
  setupFilesAfterEnv: ['./jest.setup.js'],
  moduleFileExtensions: [
    'js',
    'jsx',
    'json',
    // tell Jest to handle *.vue files
    'vue',
    'ts',
    'tsx'
  ],
  transform: {
    // process *.vue files with vue-jest
    '^.+\\.vue$': 'vue-jest',
    '.+\\.(css|styl|less|sass|scss|svg|png|jpg|ttf|woff|woff2)$':
      'jest-transform-stub',
    '^.+\\.jsx?$': 'babel-jest',
    '^.+\\.tsx?$': 'ts-jest'
  },
  transformIgnorePatterns: ['/node_modules/'],
  // support the same @ -> src alias mapping in source code
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  // serializer for snapshots
  snapshotSerializers: ['jest-serializer-vue'],
  testMatch: [
    '**/tests/e2e/**/*.spec.(js|jsx|ts|tsx)|**/__tests__/*.(js|jsx|ts|tsx)'
  ],
  // https://github.com/facebook/jest/issues/6766
  testURL: 'http://localhost/',
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ],
  globals: {
    globals: {
      NODE_ENV: 'test'
    },
    'ts-jest': {
      babelConfig: true
    }
  }
};
