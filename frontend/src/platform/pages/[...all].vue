<route lang="yaml">
meta:
  layout: auto
  requiresAuth: false
  breadcrumb: notFound.title
</route>

<template>
  <div class="flex flex-col items-center justify-center h-full text-center gap-4">
    <p class="text-8xl font-bold text-muted-foreground/30">404</p>
    <div class="space-y-1">
      <h1 class="text-xl font-semibold">{{ $t('notFound.title') }}</h1>
      <p class="text-sm text-muted-foreground">{{ $t('notFound.description') }}</p>
    </div>
    <RouterLink to="/">
      <Button variant="default">{{ $t('notFound.goHome') }}</Button>
    </RouterLink>
  </div>
</template>
