import { isRef, type App, type Directive, type DirectiveBinding, type Ref } from 'vue'
import { createLoading, type LoadingInstance } from '@/components/common/Loading'

type LoadingElement = HTMLElement & { __loadingInstance?: LoadingInstance }
type LoadingValue = boolean | Ref<boolean>

const resolveLoading = (v: LoadingValue | null | undefined) => Boolean(isRef(v) ? v.value : v)
const resolveSize = (v: string | null): 'small' | 'medium' | 'large' =>
  v === 'small' || v === 'large' ? v : 'medium'

const loadingDirective: Directive<LoadingElement, LoadingValue> = {
  mounted(el, binding: DirectiveBinding<LoadingValue>) {
    const fullscreen = Boolean(binding.modifiers.fullscreen)
    el.__loadingInstance = createLoading({
      tip: el.getAttribute('loading-tip'),
      background: el.getAttribute('loading-background'),
      size: resolveSize(el.getAttribute('loading-size')),
      loading: resolveLoading(binding.value),
      absolute: !fullscreen,
    }, fullscreen ? document.body : el)
  },
  updated(el, binding) {
    if (resolveLoading(binding.oldValue) !== resolveLoading(binding.value)) {
      el.__loadingInstance?.setLoading(resolveLoading(binding.value))
    }
  },
  unmounted(el) {
    el.__loadingInstance?.close()
    delete el.__loadingInstance
  },
}

export function setupLoadingDirective(app: App) { app.directive('loading', loadingDirective) }
export default loadingDirective
