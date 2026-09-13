import { useToast as useShadcnToast } from '@/platform/components/ui/toast/use-toast'

export function useToast() {
  const { toast } = useShadcnToast()
  return { toast }
}
