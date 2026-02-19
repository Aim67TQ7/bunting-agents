import rateLimit from 'express-rate-limit';
import { redisHelpers } from '../config/redis';
import { Request, Response } from 'express';

// Custom Redis store for rate limiting
const redisStore = {
  increment: async (key: string) => {
    const windowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000');
    const count = await redisHelpers.incrementRateLimit(key, windowMs);
    return {
      totalHits: count,
      resetTime: new Date(Date.now() + windowMs)
    };
  },
  decrement: async (key: string) => {
    // Not needed for our use case
  },
  resetKey: async (key: string) => {
    // Not needed for our use case
  }
};

// General rate limiter
export const rateLimiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000'), // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100'),
  message: 'Too many requests from this IP, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    return req.ip || 'unknown';
  },
  skip: (req: Request) => {
    // Skip rate limiting for health checks
    return req.path === '/health';
  }
});

// Strict rate limiter for auth endpoints
export const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 requests per window
  message: 'Too many authentication attempts, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: true
});

// API rate limiter with higher limits for authenticated users
export const apiRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: (req: Request) => {
    // Higher limits for authenticated users
    if ((req as any).user) {
      return 1000;
    }
    return 100;
  },
  message: 'API rate limit exceeded',
  standardHeaders: true,
  legacyHeaders: false
});