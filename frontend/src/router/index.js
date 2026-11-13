import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('@/views/Login.vue') },
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/books',
    component: () => import('@/views/BookList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/borrows',
    component: () => import('@/views/BorrowList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/readers',
    component: () => import('@/views/ReaderList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/categories',
    component: () => import('@/views/CategoryList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/users',
    component: () => import('@/views/UserList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    component: () => import('@/views/SystemSettings.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const loggedIn = !!localStorage.getItem('token')
  if (to.meta.requiresAuth && !loggedIn) return '/login'
  if (to.path === '/login' && loggedIn) return '/'
})

export default router
