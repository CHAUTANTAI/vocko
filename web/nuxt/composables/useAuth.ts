import { storeToRefs } from 'pinia'

export function useAuth() {
  const store = useAuthStore()
  const { token, refreshToken, user } = storeToRefs(store)
  return {
    token,
    refreshToken,
    user,
    login: (email: string, password: string, remember = true) => store.login(email, password, remember),
    register: (email: string, password: string, display_name: string, remember = true) =>
      store.register(email, password, display_name, remember),
    logout: () => store.logout(),
    tryRefresh: () => store.tryRefresh(),
  }
}
