import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { User } from '../models/User';
import { District } from '../models/District';
import { AppError, asyncHandler } from '../middleware/errorHandler';
import { generateTokens } from '../middleware/auth';
import { AuthRequest } from '../middleware/auth';
import { redisHelpers } from '../config/redis';
import { logger } from '../utils/logger';

export class AuthController {
  register = asyncHandler(async (req: Request, res: Response, next: NextFunction) => {
    const { email, password, firstName, lastName, districtId, role, phone } = req.body;

    // Check if user already exists
    const existingUser = await User.findOne({ where: { email } });
    if (existingUser) {
      return next(new AppError('User with this email already exists', 409));
    }

    // Verify district exists
    const district = await District.findByPk(districtId);
    if (!district) {
      return next(new AppError('Invalid district ID', 400));
    }

    // Create user
    const user = await User.create({
      email,
      password,
      firstName,
      lastName,
      districtId,
      role,
      phone,
      emailVerificationToken: crypto.randomBytes(32).toString('hex')
    });

    // Generate tokens
    const tokens = await generateTokens(user);

    // TODO: Send verification email

    res.status(201).json({
      success: true,
      message: 'User registered successfully. Please check your email to verify your account.',
      tokens,
      user: {
        id: user.id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role,
        districtId: user.districtId
      }
    });
  });

  login = asyncHandler(async (req: Request, res: Response, next: NextFunction) => {
    const { email, password } = req.body;

    // Find user and include district
    const user = await User.findOne({
      where: { email },
      include: [{ model: District, attributes: ['id', 'name'] }]
    });

    if (!user || !(await user.comparePassword(password))) {
      return next(new AppError('Invalid email or password', 401));
    }

    if (!user.active) {
      return next(new AppError('Your account has been deactivated', 401));
    }

    // Update last login
    user.lastLoginAt = new Date();
    await user.save();

    // Generate tokens
    const tokens = await generateTokens(user);

    logger.info(`User ${user.email} logged in successfully`);

    res.json({
      success: true,
      tokens,
      user: {
        id: user.id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role,
        districtId: user.districtId,
        district: user.district
      }
    });
  });

  refreshToken = asyncHandler(async (req: Request, res: Response, next: NextFunction) => {
    const { refreshToken } = req.body;

    if (!refreshToken) {
      return next(new AppError('Refresh token required', 400));
    }

    try {
      // Verify refresh token
      const decoded = jwt.verify(
        refreshToken,
        process.env.JWT_REFRESH_SECRET || 'refresh-secret'
      ) as any;

      // Check if session exists
      const session = await redisHelpers.getSession(decoded.sessionId);
      if (!session) {
        return next(new AppError('Invalid refresh token', 401));
      }

      // Get user
      const user = await User.findByPk(decoded.id);
      if (!user || !user.active) {
        return next(new AppError('User not found or inactive', 401));
      }

      // Generate new tokens
      const tokens = await generateTokens(user);

      res.json({
        success: true,
        tokens
      });
    } catch (error) {
      return next(new AppError('Invalid refresh token', 401));
    }
  });

  logout = asyncHandler(async (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new AppError('Not authenticated', 401));
    }

    // Extract session ID from token
    const authHeader = req.headers.authorization;
    const token = authHeader?.substring(7);
    
    if (token) {
      const decoded = jwt.decode(token) as any;
      if (decoded?.sessionId) {
        await redisHelpers.deleteSession(decoded.sessionId);
      }
    }

    res.json({
      success: true,
      message: 'Logged out successfully'
    });
  });

  getMe = asyncHandler(async (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new AppError('Not authenticated', 401));
    }

    const user = await User.findByPk(req.user.id, {
      attributes: { exclude: ['password'] },
      include: [{ model: District, attributes: ['id', 'name', 'subscriptionTier'] }]
    });

    if (!user) {
      return next(new AppError('User not found', 404));
    }

    res.json({
      success: true,
      user
    });
  });

  changePassword = asyncHandler(async (req: AuthRequest, res: Response, next: NextFunction) => {
    const { currentPassword, newPassword } = req.body;

    if (!req.user) {
      return next(new AppError('Not authenticated', 401));
    }

    const user = await User.findByPk(req.user.id);
    if (!user) {
      return next(new AppError('User not found', 404));
    }

    // Verify current password
    const isValidPassword = await user.comparePassword(currentPassword);
    if (!isValidPassword) {
      return next(new AppError('Current password is incorrect', 401));
    }

    // Update password
    user.password = newPassword;
    await user.save();

    res.json({
      success: true,
      message: 'Password changed successfully'
    });
  });

  forgotPassword = asyncHandler(async (req: Request, res: Response, next: NextFunction) => {
    const { email } = req.body;

    const user = await User.findOne({ where: { email } });
    if (!user) {
      return next(new AppError('No user found with this email', 404));
    }

    // Generate reset token
    const resetToken = crypto.randomBytes(32).toString('hex');
    const hashedToken = crypto
      .createHash('sha256')
      .update(resetToken)
      .digest('hex');

    // Save hashed token to user
    user.resetPasswordToken = hashedToken;
    user.resetPasswordExpires = new Date(Date.now() + 3600000); // 1 hour
    await user.save();

    // TODO: Send reset email with token

    res.json({
      success: true,
      message: 'Password reset email sent',
      // In development, return the token (remove in production)
      ...(process.env.NODE_ENV === 'development' && { resetToken })
    });
  });

  resetPassword = asyncHandler(async (req: Request, res: Response, next: NextFunction) => {
    const { token, newPassword } = req.body;

    // Hash the token
    const hashedToken = crypto
      .createHash('sha256')
      .update(token)
      .digest('hex');

    // Find user with valid token
    const user = await User.findOne({
      where: {
        resetPasswordToken: hashedToken,
        resetPasswordExpires: { $gt: new Date() }
      }
    });

    if (!user) {
      return next(new AppError('Invalid or expired reset token', 400));
    }

    // Update password
    user.password = newPassword;
    user.resetPasswordToken = null;
    user.resetPasswordExpires = null;
    await user.save();

    res.json({
      success: true,
      message: 'Password reset successfully'
    });
  });
}