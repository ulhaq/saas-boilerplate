---
name: localize
description: Add a new i18n key to all locale files (frontend/src/locales/en.ts and da.ts) and wire it into the specified component. Keeps locale files in sync across all supported languages.
argument-hint: <key.path> "<english text>" [component-path]
---

# Localize

Add a new i18n key to all frontend locale files and wire it into a component.

## Arguments

The user invoked this with: $ARGUMENTS

Parse the arguments:
- First argument: dot-separated key path (e.g. `users.invite.title` or `settings.danger.deleteConfirm`)
- Second argument (quoted string): the English text value
- Third argument (optional): path to the component where the key should be used

If arguments are missing or ambiguous, ask the user for the key path, English text, and the component file before proceeding.

## Locale file format

The locale files are TypeScript modules that export a default object:
- `frontend/src/locales/en.ts` - English (source of truth)
- `frontend/src/locales/da.ts` - Danish

Both files must always be updated together. Never add a key to one without adding it to the other.

## Workflow

### Step 1 - Read both locale files

Read `frontend/src/locales/en.ts` and `frontend/src/locales/da.ts` to understand the existing structure and find the right insertion point for the new key.

### Step 2 - Check for duplicates

Search for the key path in the locale files to ensure it doesn't already exist:
```bash
grep -n "<key-segment>" frontend/src/locales/en.ts
```

If it already exists, report the existing value and ask whether to update it.

### Step 3 - Add the key to en.ts

Insert the new key at the correct nested position in `frontend/src/locales/en.ts`. Maintain consistent formatting (2-space indent, trailing commas).

Example - adding `users.invite.title: "Invite User"`:
```ts
users: {
  // existing keys...
  invite: {
    title: "Invite User",  // ← new key
  },
},
```

### Step 4 - Add the key to da.ts

Add the same key to `frontend/src/locales/da.ts`. For Danish translations:
- If the user provided a Danish translation in the arguments, use it
- Otherwise, use the English text as a placeholder and add a comment: `// TODO: translate`

Keep the structure in `da.ts` mirrored exactly to `en.ts`.

### Step 5 - Wire into the component (if provided)

If a component path was given, read the component file and add the key usage:

In `<template>`: use `$t('key.path')`
In `<script setup>`: use `const { t } = useI18n()` then `t('key.path')`

Check whether `useI18n` is already imported in the component. If not, add:
```ts
const { t } = useI18n()
```

Find the relevant hardcoded string (if any) and replace it with the `t()` call.

### Step 6 - Verify TypeScript

```bash
cd frontend && npm run typecheck
```

Fix any type errors before reporting done.

## Key namespace conventions

| Prefix | Used for |
|---|---|
| `auth.*` | Login, register, password reset pages |
| `nav.*` | Sidebar and top navigation labels |
| `common.*` | Shared labels (Save, Cancel, Delete, etc.) |
| `settings.*` | Settings pages |
| `errors.api.*` | API error messages |
| `errors.fields.*` | Form field validation errors |
| `<resource>.*` | Resource-specific labels (e.g. `users.*`, `roles.*`) |

Choose the most specific applicable namespace.
