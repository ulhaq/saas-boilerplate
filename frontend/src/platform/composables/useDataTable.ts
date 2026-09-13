import { ref, reactive, computed } from 'vue'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import type { PaginatedResponse, FilterOp } from '@/platform/types'

type FetcherParams = Record<string, string | number | undefined>

interface UseDataTableOptions<T> {
  fetcher: (params: FetcherParams) => Promise<PaginatedResponse<T>>
  defaultPageSize?: number
  immediate?: boolean
}

export function useDataTable<T>(options: UseDataTableOptions<T>) {
  const { fetcher, defaultPageSize = 20, immediate = true } = options
  const { resolveError } = useErrorHandler()

  const items = ref<T[]>([])
  const total = ref(0)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const pagination = reactive({ page: 1, pageSize: defaultPageSize })
  const currentSort = ref<string | undefined>(undefined)
  const currentFilters = ref<Record<string, { v: (string | number | boolean)[]; op: FilterOp }>>({})
  const currentSearch = ref<string | undefined>(undefined)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pagination.pageSize)))

  async function fetchData() {
    isLoading.value = true
    error.value = null
    try {
      const filterParams: FetcherParams = {}
      for (const [field, { v, op }] of Object.entries(currentFilters.value)) {
        filterParams[`${field}__${op}`] = v.join(',')
      }

      const data = await fetcher({
        page_number: pagination.page,
        page_size: pagination.pageSize,
        sort: currentSort.value,
        q: currentSearch.value,
        ...filterParams,
      })
      items.value = data.items
      total.value = data.total
    } catch (err: unknown) {
      error.value = resolveError(err)
    } finally {
      isLoading.value = false
    }
  }

  function goToPage(page: number) {
    pagination.page = page
    fetchData()
  }

  function setPageSize(size: number) {
    pagination.pageSize = size
    pagination.page = 1
    fetchData()
  }

  function setSort(field: string, desc = false) {
    currentSort.value = field ? (desc ? `-${field}` : field) : undefined
    pagination.page = 1
    fetchData()
  }

  function setFilters(
    entries: { field: string; value: (string | number | boolean)[]; op?: FilterOp }[],
  ) {
    for (const { field, value, op = 'ico' } of entries) {
      if (value.length === 0) {
        delete currentFilters.value[field]
      } else {
        currentFilters.value[field] = { v: value, op }
      }
    }
    pagination.page = 1
    fetchData()
  }

  function setSearch(term: string | undefined) {
    currentSearch.value = term || undefined
    pagination.page = 1
    fetchData()
  }

  function refresh() {
    fetchData()
  }

  if (immediate) {
    fetchData()
  }

  return {
    items,
    total,
    isLoading,
    error,
    pagination,
    totalPages,
    fetchData,
    goToPage,
    setPageSize,
    setSort,
    setFilters,
    setSearch,
    refresh,
  }
}
