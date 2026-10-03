import { useToast as useShadcnToast } from '@/foundation/components/ui/toast/use-toast'

export function useToast() {
  const { toast } = useShadcnToast()
  return { toast }
}
