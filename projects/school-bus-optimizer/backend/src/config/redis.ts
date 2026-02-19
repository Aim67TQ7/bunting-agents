import { createClient } from 'redis';
import { logger } from '../utils/logger';

const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';

export const redisClient = createClient({
  url: redisUrl,
  socket: {
    reconnectStrategy: (retries) => {
      if (retries > 10) {
        logger.error('Redis: Max reconnection attempts reached');
        return new Error('Max reconnection attempts reached');
      }
      const delay = Math.min(retries * 100, 3000);
      logger.info(`Redis: Reconnecting in ${delay}ms...`);
      return delay;
    }
  }
});

redisClient.on('error', (err) => {
  logger.error('Redis Client Error:', err);
});

redisClient.on('connect', () => {
  logger.info('Redis Client Connected');
});

redisClient.on('ready', () => {
  logger.info('Redis Client Ready');
});

// Helper functions for common Redis operations
export const redisHelpers = {
  // Cache GPS positions
  async setGPSPosition(busId: string, position: any, ttl = 300) {
    const key = `gps:${busId}`;
    await redisClient.setEx(key, ttl, JSON.stringify(position));
  },

  async getGPSPosition(busId: string) {
    const key = `gps:${busId}`;
    const data = await redisClient.get(key);
    return data ? JSON.parse(data) : null;
  },

  // Cache route optimization results
  async setOptimizedRoute(districtId: string, routeData: any, ttl = 3600) {
    const key = `route:optimized:${districtId}`;
    await redisClient.setEx(key, ttl, JSON.stringify(routeData));
  },

  async getOptimizedRoute(districtId: string) {
    const key = `route:optimized:${districtId}`;
    const data = await redisClient.get(key);
    return data ? JSON.parse(data) : null;
  },

  // Session management
  async setSession(sessionId: string, userData: any, ttl = 86400) {
    const key = `session:${sessionId}`;
    await redisClient.setEx(key, ttl, JSON.stringify(userData));
  },

  async getSession(sessionId: string) {
    const key = `session:${sessionId}`;
    const data = await redisClient.get(key);
    return data ? JSON.parse(data) : null;
  },

  async deleteSession(sessionId: string) {
    const key = `session:${sessionId}`;
    await redisClient.del(key);
  },

  // Rate limiting
  async incrementRateLimit(identifier: string, windowMs: number) {
    const key = `ratelimit:${identifier}`;
    const multi = redisClient.multi();
    multi.incr(key);
    multi.expire(key, Math.ceil(windowMs / 1000));
    const results = await multi.exec();
    return results?.[0] || 0;
  }
};