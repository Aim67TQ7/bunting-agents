import { Router } from 'express';
import { authenticate, authorize } from '../middleware/auth';

const router = Router();

// GPS tracking endpoints
router.use(authenticate);

// Update bus location (driver only)
router.post('/buses/:busId/location', authorize('driver', 'admin'));

// Get bus current location
router.get('/buses/:busId/location');

// Get bus tracking history
router.get('/buses/:busId/history');

// Subscribe to real-time tracking (returns WebSocket connection info)
router.post('/buses/:busId/subscribe');

export default router;