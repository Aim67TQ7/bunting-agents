import { Server, Socket } from 'socket.io';
import jwt from 'jsonwebtoken';
import { GPSTracking } from '../models/GPSTracking';
import { Bus } from '../models/Bus';
import { Route } from '../models/Route';
import { RouteStop } from '../models/RouteStop';
import { redisHelpers } from '../config/redis';
import { logger } from '../utils/logger';

interface AuthenticatedSocket extends Socket {
  userId?: string;
  role?: string;
  districtId?: string;
  busId?: string;
}

interface GPSUpdate {
  busId: string;
  lat: number;
  lng: number;
  speed?: number;
  heading?: number;
  timestamp?: Date;
}

export function setupWebSocket(io: Server) {
  // Authentication middleware
  io.use(async (socket: AuthenticatedSocket, next) => {
    try {
      const token = socket.handshake.auth.token;
      if (!token) {
        return next(new Error('Authentication required'));
      }

      const decoded = jwt.verify(
        token,
        process.env.JWT_SECRET || 'secret'
      ) as any;

      socket.userId = decoded.id;
      socket.role = decoded.role;
      socket.districtId = decoded.districtId;

      next();
    } catch (error) {
      next(new Error('Invalid token'));
    }
  });

  io.on('connection', (socket: AuthenticatedSocket) => {
    logger.info(`WebSocket connected: ${socket.id} (User: ${socket.userId})`);

    // Join district room for broadcast messages
    if (socket.districtId) {
      socket.join(`district:${socket.districtId}`);
    }

    // Driver-specific handlers
    if (socket.role === 'driver') {
      handleDriverConnection(socket, io);
    }

    // Parent-specific handlers
    if (socket.role === 'parent') {
      handleParentConnection(socket, io);
    }

    // Admin/District admin handlers
    if (socket.role === 'admin' || socket.role === 'district_admin') {
      handleAdminConnection(socket, io);
    }

    // Common handlers
    socket.on('disconnect', () => {
      logger.info(`WebSocket disconnected: ${socket.id}`);
      handleDisconnect(socket);
    });

    socket.on('error', (error) => {
      logger.error(`WebSocket error for ${socket.id}:`, error);
    });
  });
}

function handleDriverConnection(socket: AuthenticatedSocket, io: Server) {
  // Driver joins their bus room
  socket.on('join:bus', async (busId: string) => {
    try {
      // Verify driver is assigned to this bus
      const bus = await Bus.findByPk(busId);
      if (!bus || bus.driverId !== socket.userId) {
        socket.emit('error', 'Unauthorized: Not assigned to this bus');
        return;
      }

      socket.busId = busId;
      socket.join(`bus:${busId}`);
      socket.emit('joined:bus', { busId });
      
      logger.info(`Driver ${socket.userId} joined bus ${busId}`);
    } catch (error) {
      logger.error('Error joining bus room:', error);
      socket.emit('error', 'Failed to join bus room');
    }
  });

  // GPS update from driver
  socket.on('gps:update', async (data: GPSUpdate) => {
    try {
      if (!socket.busId || socket.busId !== data.busId) {
        socket.emit('error', 'Unauthorized GPS update');
        return;
      }

      // Save to database
      const tracking = await GPSTracking.create({
        busId: data.busId,
        lat: data.lat,
        lng: data.lng,
        speed: data.speed,
        heading: data.heading,
        timestamp: data.timestamp || new Date()
      });

      // Cache latest position
      await redisHelpers.setGPSPosition(data.busId, {
        lat: data.lat,
        lng: data.lng,
        speed: data.speed,
        heading: data.heading,
        timestamp: tracking.timestamp
      });

      // Broadcast to all subscribers of this bus
      io.to(`bus:${data.busId}`).emit('gps:position', {
        busId: data.busId,
        lat: data.lat,
        lng: data.lng,
        speed: data.speed,
        heading: data.heading,
        timestamp: tracking.timestamp
      });

      // Broadcast to district admins
      io.to(`district:${socket.districtId}:admins`).emit('gps:position', {
        busId: data.busId,
        lat: data.lat,
        lng: data.lng,
        speed: data.speed,
        heading: data.heading,
        timestamp: tracking.timestamp
      });

      // Calculate ETAs for upcoming stops
      await calculateAndBroadcastETAs(data.busId, io);

    } catch (error) {
      logger.error('Error updating GPS position:', error);
      socket.emit('error', 'Failed to update GPS position');
    }
  });

  // Driver status updates
  socket.on('status:update', async (data: { status: string; message?: string }) => {
    try {
      if (!socket.busId) {
        socket.emit('error', 'No bus assigned');
        return;
      }

      // Broadcast status to subscribers
      io.to(`bus:${socket.busId}`).emit('bus:status', {
        busId: socket.busId,
        status: data.status,
        message: data.message,
        timestamp: new Date()
      });

      logger.info(`Bus ${socket.busId} status: ${data.status}`);
    } catch (error) {
      logger.error('Error updating bus status:', error);
      socket.emit('error', 'Failed to update status');
    }
  });
}

function handleParentConnection(socket: AuthenticatedSocket, io: Server) {
  // Parent subscribes to their child's bus
  socket.on('subscribe:bus', async (studentId: string) => {
    try {
      // Find active route for this student
      const routeStop = await RouteStop.findOne({
        where: { studentId },
        include: [{
          model: Route,
          where: { active: true },
          include: [{ model: Bus }]
        }]
      });

      if (!routeStop || !routeStop.route || !routeStop.route.bus) {
        socket.emit('error', 'No active route found for student');
        return;
      }

      const busId = routeStop.route.busId;
      socket.join(`bus:${busId}`);
      socket.emit('subscribed:bus', {
        busId,
        routeId: routeStop.route.id,
        stopOrder: routeStop.stopOrder,
        scheduledTime: routeStop.scheduledTime
      });

      // Send current bus position if available
      const currentPosition = await redisHelpers.getGPSPosition(busId);
      if (currentPosition) {
        socket.emit('gps:position', {
          busId,
          ...currentPosition
        });
      }

      logger.info(`Parent ${socket.userId} subscribed to bus ${busId}`);
    } catch (error) {
      logger.error('Error subscribing to bus:', error);
      socket.emit('error', 'Failed to subscribe to bus');
    }
  });

  // Parent requests ETA
  socket.on('request:eta', async (data: { busId: string; studentId: string }) => {
    try {
      const eta = await calculateStudentETA(data.busId, data.studentId);
      socket.emit('eta:update', eta);
    } catch (error) {
      logger.error('Error calculating ETA:', error);
      socket.emit('error', 'Failed to calculate ETA');
    }
  });
}

function handleAdminConnection(socket: AuthenticatedSocket, io: Server) {
  // Admin joins district admin room
  socket.join(`district:${socket.districtId}:admins`);

  // Admin subscribes to all buses in district
  socket.on('subscribe:all-buses', async () => {
    try {
      const buses = await Bus.findAll({
        where: { districtId: socket.districtId, active: true }
      });

      for (const bus of buses) {
        socket.join(`bus:${bus.id}`);
      }

      socket.emit('subscribed:all-buses', {
        busCount: buses.length,
        busIds: buses.map(b => b.id)
      });

      // Send current positions
      const positions = await Promise.all(
        buses.map(async (bus) => {
          const position = await redisHelpers.getGPSPosition(bus.id);
          return position ? { busId: bus.id, ...position } : null;
        })
      );

      socket.emit('gps:bulk-positions', positions.filter(p => p !== null));

    } catch (error) {
      logger.error('Error subscribing to all buses:', error);
      socket.emit('error', 'Failed to subscribe to buses');
    }
  });

  // Admin can send announcements
  socket.on('announcement:send', async (data: { message: string; targetBusId?: string }) => {
    try {
      if (data.targetBusId) {
        io.to(`bus:${data.targetBusId}`).emit('announcement', {
          message: data.message,
          timestamp: new Date(),
          from: 'dispatch'
        });
      } else {
        io.to(`district:${socket.districtId}`).emit('announcement', {
          message: data.message,
          timestamp: new Date(),
          from: 'dispatch'
        });
      }
    } catch (error) {
      logger.error('Error sending announcement:', error);
      socket.emit('error', 'Failed to send announcement');
    }
  });
}

async function calculateAndBroadcastETAs(busId: string, io: Server) {
  try {
    // Get current bus position
    const currentPosition = await redisHelpers.getGPSPosition(busId);
    if (!currentPosition) return;

    // Get active route and remaining stops
    const route = await Route.findOne({
      where: { busId, active: true },
      include: [{
        model: RouteStop,
        order: [['stopOrder', 'ASC']]
      }]
    });

    if (!route || !route.stops) return;

    // Calculate ETAs for each stop
    const etas = [];
    let accumulatedTime = 0;

    for (const stop of route.stops) {
      // Skip stops that have been completed
      if (stop.actualTime) continue;

      // Simple ETA calculation (would use Google Maps in production)
      const distance = calculateDistance(
        currentPosition.lat,
        currentPosition.lng,
        stop.lat,
        stop.lng
      );

      // Assume average speed of 25 mph
      const timeToStop = (distance / 25) * 60; // minutes
      accumulatedTime += timeToStop + 1; // 1 minute per stop

      const eta = new Date(Date.now() + accumulatedTime * 60000);
      
      etas.push({
        stopId: stop.id,
        studentId: stop.studentId,
        eta: eta,
        estimatedMinutes: Math.round(accumulatedTime)
      });

      // Update estimated time in database
      stop.estimatedTime = eta.toTimeString().slice(0, 5);
      await stop.save();
    }

    // Broadcast ETAs
    io.to(`bus:${busId}`).emit('eta:bulk-update', {
      busId,
      etas,
      timestamp: new Date()
    });

  } catch (error) {
    logger.error('Error calculating ETAs:', error);
  }
}

async function calculateStudentETA(busId: string, studentId: string) {
  const currentPosition = await redisHelpers.getGPSPosition(busId);
  if (!currentPosition) {
    throw new Error('Bus position not available');
  }

  const routeStop = await RouteStop.findOne({
    where: { studentId },
    include: [{
      model: Route,
      where: { busId, active: true }
    }]
  });

  if (!routeStop) {
    throw new Error('Student not found on active route');
  }

  // Simple distance calculation
  const distance = calculateDistance(
    currentPosition.lat,
    currentPosition.lng,
    routeStop.lat,
    routeStop.lng
  );

  const estimatedMinutes = Math.round((distance / 25) * 60);
  const eta = new Date(Date.now() + estimatedMinutes * 60000);

  return {
    studentId,
    eta,
    estimatedMinutes,
    scheduledTime: routeStop.scheduledTime,
    stopOrder: routeStop.stopOrder
  };
}

function calculateDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 3959; // Earth's radius in miles
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function toRad(degrees: number): number {
  return degrees * (Math.PI / 180);
}

function handleDisconnect(socket: AuthenticatedSocket) {
  // Clean up any tracking state
  if (socket.busId && socket.role === 'driver') {
    // Notify subscribers that driver disconnected
    socket.to(`bus:${socket.busId}`).emit('driver:disconnected', {
      busId: socket.busId,
      timestamp: new Date()
    });
  }
}