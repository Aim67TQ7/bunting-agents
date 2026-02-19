import { Router } from 'express';
import { authenticate, authorize, validateDistrictAccess } from '../middleware/auth';

const router = Router();

// All route endpoints require authentication
router.use(authenticate);

// Get all routes for a district
router.get('/district/:districtId', validateDistrictAccess);

// Optimize routes for a district
router.post('/district/:districtId/optimize', validateDistrictAccess, authorize('admin', 'district_admin'));

// Get single route
router.get('/:routeId');

// Update route
router.put('/:routeId', authorize('admin', 'district_admin'));

// Delete route
router.delete('/:routeId', authorize('admin', 'district_admin'));

// Get route stops
router.get('/:routeId/stops');

// Update route stops
router.put('/:routeId/stops', authorize('admin', 'district_admin'));

export default router;