import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './pages/Dashboard.vue'
import AccountList from './pages/AccountList.vue'
import AccountDetail from './pages/AccountDetail.vue'
import Workbench from './pages/Workbench.vue'
import TierRules from './pages/TierRules.vue'
import PeakHours from './pages/PeakHours.vue'
import PeakCompare from './pages/PeakCompare.vue'
import RunHistory from './pages/RunHistory.vue'
import Settings from './pages/Settings.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/accounts', component: AccountList },
    { path: '/accounts/:id', component: AccountDetail },
    { path: '/workbench', component: Workbench },
    { path: '/tiers', component: TierRules },
    { path: '/peak-windows', component: PeakHours },
    { path: '/compare', component: PeakCompare },
    { path: '/history', component: RunHistory },
    { path: '/settings', component: Settings },
  ],
})
