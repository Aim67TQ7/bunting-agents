import { Router } from 'express';
import { authenticate, authorize, validateDistrictAccess } from '../middleware/auth';

const router = Router();

// All bus routes require authentication
router.use(authenticate);

// Get all buses for a district
router.get('/district/:districtId', validateDistrictAccess);

// Create new bus
router.post('/', authorize('admin', 'district_admin'));

// Get single bus
router.get('/:busId');

// Update bus
router.put('/:busId', authorize('admin', 'district_admin'));

// Delete bus
router.delete('/:busId', authorize('admin', 'district_admin'));

// Update bus status
router.patch('/:busId/status', authorize('admin', 'district_admin', 'driver'));

export default router;