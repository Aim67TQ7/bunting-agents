import { Router } from 'express';
import { authenticate, authorize, validateDistrictAccess } from '../middleware/auth';

const router = Router();

// All driver routes require authentication
router.use(authenticate);

// Get all drivers for a district
router.get('/district/:districtId', validateDistrictAccess);

// Create new driver
router.post('/', authorize('admin', 'district_admin'));

// Get single driver
router.get('/:driverId');

// Update driver
router.put('/:driverId', authorize('admin', 'district_admin'));

// Delete driver
router.delete('/:driverId', authorize('admin', 'district_admin'));

// Get driver schedule
router.get('/:driverId/schedule');

export default router;