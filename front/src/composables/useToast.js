import { reactive } from 'vue'

export function useToast() {
  const toast = reactive({ message: '', type: 'info', timer: null })

  function showToast(message, type = 'info') {
    toast.message = message
    toast.type = type
    clearTimeout(toast.timer)
    toast.timer = setTimeout(() => {
      toast.message = ''
    }, 3600)
  }

  return { toast, showToast }
}
