import '@testing-library/jest-dom/vitest'

// jsdom does not implement URL.createObjectURL; provide stubs for tests that
// trigger file preview rendering in components using object URLs.
if (typeof URL.createObjectURL === 'undefined') {
  URL.createObjectURL = () => 'blob:mock-object-url'
}
if (typeof URL.revokeObjectURL === 'undefined') {
  URL.revokeObjectURL = () => {}
}
