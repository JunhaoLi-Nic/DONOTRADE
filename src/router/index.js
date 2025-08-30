import { createRouter, createWebHistory } from 'vue-router'
import LoginRegisterLayout from '../layouts/LoginRegister.vue'
import DashboardLayout from '../layouts/Dashboard.vue'
import { registerOff } from '../stores/globals'
import axios from 'axios'
import { AuthService } from '../services/auth'

// Add Strategy Backtest import
import StrategyBacktest from '../views/StrategyBacktest.vue'

// Initialize registration status once without self-executing async function
function getRegisterPage() {
    console.log("\nGETTING REGISTER PAGE")
    axios.post('/api/registerPage')
        .then((response) => {
            registerOff.value = response.data.registerOff !== undefined ? response.data.registerOff : response.data.register_off || false
            console.log("Register page status:", registerOff.value)
        })
        .catch((error) => {
            console.log(" -> Error getting register page " + error)
        });
}

// Call the function once at startup
getRegisterPage();

const router = createRouter({
    history: createWebHistory(
        import.meta.env.BASE_URL),
    routes: [{
        path: '/',
        name: 'login',
        meta: {
            title: "Login",
            layout: LoginRegisterLayout,
            requiresAuth: false
        },
        component: () =>
            import('../views/Login.vue')
    },
    {
        path: '/register',
        name: 'register',
        meta: {
            title: "Register",
            layout: LoginRegisterLayout,
            requiresAuth: false
        },
        component: () =>
            import('../views/Register.vue')
    },
    {
        path: '/dashboard',
        name: 'dashboard',
        meta: {
            title: "Dashboard",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Dashboard.vue')
    },
    {
        path: '/calendar',
        name: 'calendar',
        meta: {
            title: "Calendar",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Calendar.vue')
    },
    {
        path: '/riskmanagement',
        name: 'riskmanagement',
        meta: {
            title: "Risk Management",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/RiskManagement.vue')
    },
    {
        path: '/catalysts',
        name: 'catalysts',
        meta: {
            title: "Market Catalysts",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Catalysts.vue')
    },
    {
        path: '/daily',
        name: 'daily',
        meta: {
            title: "Daily",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Daily.vue')
    },
    {
        path: '/diary',
        name: 'diary',
        meta: {
            title: "Diary",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Diary.vue')
    },
    {
        path: '/screenshots',
        name: 'screenshots',
        meta: {
            title: "Screenshots",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Screenshots.vue')
    },
    {
        path: '/playbook',
        name: 'playbook',
        meta: {
            title: "Playbook",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Playbook.vue')
    },
    {
        path: '/playbook/:id',
        name: 'playbookDetail',
        meta: {
            title: "Playbook Detail",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/PlaybookDetail.vue')
    },
    {
        path: '/addTrades',
        name: 'addTrades',
        meta: {
            title: "Add Trades",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/AddTrades.vue')
        
    },
    {
        path: '/addDiary',
        name: 'addDiary',
        meta: {
            title: "Add Diary",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/AddDiary.vue')
    },
    {
        path: '/addPlaybook',
        name: 'addPlaybook',
        meta: {
            title: "Add Playbook",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/AddPlaybook.vue')
    },
    {
        path: '/addScreenshot',
        name: 'addScreenshot',
        meta: {
            title: "Add Screenshot",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/AddScreenshot.vue')
    },
    {
        path: '/addExcursions',
        name: 'addExcursions',
        meta: {
            title: "Add Excursions",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/AddExcursions.vue')
    },
    {
        path: '/settings',
        name: 'settings',
        meta: {
            title: "Settings",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Settings.vue')
    },
    {
        path: '/imports',
        name: 'imports',
        meta: {
            title: "Imports",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Imports.vue')
    },
    {
        path: '/checkout',
        name: 'checkout',
        meta: {
            title: "Checkout",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Checkout.vue')
    },
    {
        path: '/checkoutSuccess',
        name: 'checkoutSuccess',
        meta: {
            title: "Checkout Success",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/CheckoutSuccess.vue')
    },
    {
        path: '/analysis',
        name: 'analysis',
        meta: {
            title: "Analysis",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/Analysis.vue')
    },
    {
        path: '/strategy-backtest',
        name: 'strategy-backtest',
        meta: {
            title: "Strategy Backtest",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/StrategyBacktest.vue')
    },
    {
        path: '/market-watchlist',
        name: 'market-watchlist',
        meta: {
            title: "Market Watchlist",
            layout: DashboardLayout,
            requiresAuth: true
        },
        component: () =>
            import('../views/MarketWatchlist.vue')
    }
    ]
})

// Global navigation guard to handle authentication
router.beforeEach((to, from, next) => {
    // Get the page title from the route meta data
    const title = to.meta.title;
    if (title) {
        document.title = title;
    }
    
    // Set login timestamp to prevent login loops during navigation
    sessionStorage.setItem('last_navigation', Date.now().toString());
    
    // Handle authentication
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
    const isAuthenticated = AuthService.isAuthenticated();
    
    if (requiresAuth && !isAuthenticated) {
        // Route requires auth but user is not logged in
        console.log("Authentication required - redirecting to login");
        next('/');
    } else if (!requiresAuth && isAuthenticated && (to.path === '/' || to.path === '/register')) {
        // User is logged in but trying to access login or register page
        console.log("Already logged in - redirecting to dashboard");
        next('/dashboard');
    } else if (to.name === 'register' && registerOff.value) {
        // Registration is disabled
        next('/');
    } else {
        // Continue with navigation
        next();
    }
})

export default router