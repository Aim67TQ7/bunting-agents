import { Router } from 'express';
import { authenticate, authorize, validateDistrictAccess } from '../middleware/auth';

const router = Router();

// All district routes require authentication
router.use(authenticate);

// Get all districts (admin only)
router.get('/', authorize('admin'));

// Get single district
router.get('/:districtId', validateDistrictAccess);

// Update district
router.put('/:districtId', validateDistrictAccess, authorize('admin', 'district_admin'));

// Get district settings
router.get('/:districtId/settings', validateDistrictAccess);

// Update district settings
router.put('/:districtId/settings', validateDistrictAccess, authorize('admin', 'district_admin'));

export default router;