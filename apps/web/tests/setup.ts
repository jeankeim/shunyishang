import '@testing-library/jest-dom';

// Mock ResizeObserver for jsdom
global.ResizeObserver = class ResizeObserver {
  private callback: ResizeObserverCallback;
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock matchMedia for jsdom (useMediaQuery / useReducedMotion 依赖，默认「无媒体偏好」)
// configurable: true —— 允许单个测试用例再覆写成自己的 mock
const noop = () => {}
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: noop,
    removeListener: noop,
    addEventListener: noop,
    removeEventListener: noop,
    dispatchEvent: noop,
  }),
});

// Proper localStorage polyfill (jsdom's --localstorage-file may be broken)
const localStorageStore: Record<string, string> = {};

const localStoragePolyfill = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => { localStorageStore[key] = String(value); },
  removeItem: (key: string) => { delete localStorageStore[key]; },
  clear: () => { Object.keys(localStorageStore).forEach(k => delete localStorageStore[k]); },
  key: (index: number) => Object.keys(localStorageStore)[index] ?? null,
  get length() { return Object.keys(localStorageStore).length; },
};

Object.defineProperty(globalThis, 'localStorage', {
  value: localStoragePolyfill,
  writable: true,
  configurable: true,
});

Object.defineProperty(window, 'localStorage', {
  value: localStoragePolyfill,
  writable: true,
  configurable: true,
});
