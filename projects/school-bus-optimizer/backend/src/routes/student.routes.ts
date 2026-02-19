import { Router } from 'express';
import { authenticate, authorize, validateDistrictAccess } from '../middleware/auth';

const router = Router();

// All student routes require authentication
router.use(authenticate);

// Get all students for a district
router.get('/district/:districtId', validateDistrictAccess);

// Create new student
router.post('/', authorize('admin', 'district_admin'));

// Get single student
router.get('/:studentId');

// Update student
router.put('/:studentId', authorize('admin', 'district_admin'));

// Delete student
router.delete('/:studentId', authorize('admin', 'district_admin'));

// Bulk import students
router.post('/import', authorize('admin', 'district_admin'));

export default router;