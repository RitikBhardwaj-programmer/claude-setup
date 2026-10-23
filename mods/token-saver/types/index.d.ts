export type WarnLevel = number

declare module 'claude-code' {
  interface PluginState {
    'token-saver': {
      /** Highest context level (tokens) the warning has fired for; 0 = none. */
      warnLevel: WarnLevel
      /** The level the person hid the band for. */
      hiddenLevel: WarnLevel
      /** True while visual design work turns screenshot shrinking off. */
      isVisual: boolean
      /** Time of the last refresh; a write redraws the /warm pane. */
      tick: number
    }
  }
}
