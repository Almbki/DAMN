declare module '*.css';
declare module '*.module.css';

// Expo inlines `process.env.EXPO_PUBLIC_*` at build time. Declared here because no
// Node types are pulled in.
declare const process: { env: Record<string, string | undefined> };
