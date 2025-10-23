export default {
  testEnvironment: 'node',
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest'
  },
  moduleFileExtensions: ['js', 'jsx'],
  testMatch: ['**/tests/**/*.js'],
  testTimeout: 20000
};
