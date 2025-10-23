module.exports = {
  env: {
    browser: true,
    node: true,
    es2022: true,
    jest: true
  },
  extends: ['airbnb-base', 'plugin:react/recommended'],
  settings: {
    react: {
      version: '18.0'
    }
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  plugins: ['react', 'react-hooks'],
  rules: {
    'no-console': 'off',
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    'import/extensions': [
      'error',
      'ignorePackages',
      {
        js: 'always',
        jsx: 'always'
      }
    ],
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn'
  }
};
