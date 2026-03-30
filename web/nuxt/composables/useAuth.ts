import { storeToRefs } from 'pinia'

export function useAuth() {
  const store = useAuthStore()
  const { token, refreshToken, user } = storeToRefs(store)
  return {
    token,
    refreshToken,
    user,
    login: (email: string, password: string) => store.login(email, password),
    register: (email: string, password: string, display_name: string) =>
      store.register(email, password, display_name),
    logout: () => store.logout(),
    tryRefresh: () => store.tryRefresh(),
  }
}
