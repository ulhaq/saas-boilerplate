/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />

declare module '*.css' {
  const content: string
  export default content
}
