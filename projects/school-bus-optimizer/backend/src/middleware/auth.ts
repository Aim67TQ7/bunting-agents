import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { AppError } from './errorHandler';
import { User } from '../models/User';
import { redisHelpers } from '../config/redis';

export interface AuthRequest extends Request {
  user?: {
    id: string;
    districtId: string;
    role: string;
    email: string;
  };
}

export const authenticate = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
) => {
  try {
    // Get token from header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new AppError('No token provided', 401);
    }

    const token = authHeader.substring(7);

    // Verify token
    const decoded = jwt.verify(
      token,
      process.env.JWT_SECRET || 'secret'
    ) as any;

    // Check if token is in Redis (for logout functionality)
    const session = await redisHelpers.getSession(decoded.sessionId);
    if (!session) {
      throw new AppError('Session expired', 401);
    }

    // Get user from database
    const user = await User.findByPk(decoded.id, {
      attributes: ['id', 'districtId', 'role', 'email', 'active']
    });

    if (!user || !user.active) {
      throw new AppError('User not found or inactive', 401);
    }

    // Attach user to request
    req.user = {
      id: user.id,
      districtId: user.districtId,
      role: user.role,
      email: user.email
    };

    next();
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      next(new AppError('Token expired', 401));
    } else if (error instanceof jwt.JsonWebTokenError) {
      next(new AppError('Invalid token', 401));
    } else {
      next(error);
    }
  }
};

// Role-based access control
export const authorize = (...roles: string[]) => {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new AppError('Authentication required', 401));
    }

    if (!roles.includes(req.user.role)) {
      return next(
        new AppError('You do not have permission to perform this action', 403)
      );
    }

    next();
  };
};

// Multi-tenant access control
export const validateDistrictAccess = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
) => {
  if (!req.user) {
    return next(new AppError('Authentication required', 401));
  }

  // Admin users can access all districts
  if (req.user.role === 'admin') {
    return next();
  }

  // Check if the requested resource belongs to user's district
  const districtId = req.params.districtId || req.body.districtId;
  
  if (districtId && districtId !== req.user.districtId) {
    return next(
      new AppError('Access denied to this district', 403)
    );
  }

  next();
};

// Generate JWT tokens
export const generateTokens = async (user: any) => {
  const sessionId = `${user.id}-${Date.now()}`;
  
  const accessToken = jwt.sign(
    {
      id: user.id,
      email: user.email,
      role: user.role,
      districtId: user.districtId,
      sessionId
    },
    process.env.JWT_SECRET || 'secret',
    {
      expiresIn: process.env.JWT_EXPIRES_IN || '15m'
    }
  );

  const refreshToken = jwt.sign(
    {
      id: user.id,
      sessionId
    },
    process.env.JWT_REFRESH_SECRET || 'refresh-secret',
    {
      expiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d'
    }
  );

  // Store session in Redis
  await redisHelpers.setSession(sessionId, {
    userId: user.id,
    email: user.email,
    role: user.role,
    districtId: user.districtId
  });

  return { accessToken, refreshToken, sessionId };
};