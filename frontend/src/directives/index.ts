import type { App } from 'vue'
import { setupDragDirective } from './drag'
import { setupLoadingDirective } from './loading'

export function setupGlobDirectives(app: App) {
  setupLoadingDirective(app)
  setupDragDirective(app)
}
