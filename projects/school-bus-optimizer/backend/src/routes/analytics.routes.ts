import { Router } from 'express';
import { authenticate, authorize, validateDistrictAccess } from '../middleware/auth';

const router = Router();

// All analytics routes require authentication
router.use(authenticate);

// Get district analytics summary
router.get('/districts/:districtId/summary', validateDistrictAccess, authorize('admin', 'district_admin'));

// Get route performance metrics
router.get('/routes/:routeId/performance', authorize('admin', 'district_admin'));

// Get cost savings report
router.get('/districts/:districtId/savings', validateDistrictAccess, authorize('admin', 'district_admin'));

// Get driver performance metrics
router.get('/drivers/:driverId/performance', authorize('admin', 'district_admin'));

// Export analytics data
router.post('/districts/:districtId/export', validateDistrictAccess, authorize('admin', 'district_admin'));

export default router;