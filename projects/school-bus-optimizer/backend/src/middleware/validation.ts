import { Request, Response, NextFunction } from 'express';
import Joi from 'joi';
import { AppError } from './errorHandler';

export const validate = (schema: Joi.ObjectSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const { error } = schema.validate(req.body, {
      abortEarly: false,
      stripUnknown: true
    });

    if (error) {
      const errorMessage = error.details
        .map(detail => detail.message)
        .join(', ');
      return next(new AppError(errorMessage, 400));
    }

    next();
  };
};

// Common validation schemas
export const schemas = {
  // Auth schemas
  register: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().min(8).required(),
    firstName: Joi.string().required(),
    lastName: Joi.string().required(),
    districtId: Joi.string().uuid().required(),
    role: Joi.string().valid('district_admin', 'driver', 'parent').required(),
    phone: Joi.string().optional()
  }),

  login: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().required()
  }),

  // District schemas
  createDistrict: Joi.object({
    name: Joi.string().required(),
    address: Joi.string().required(),
    contactEmail: Joi.string().email().required(),
    contactPhone: Joi.string().required(),
    subscriptionTier: Joi.string()
      .valid('trial', 'basic', 'professional', 'enterprise')
      .default('trial')
  }),

  updateDistrict: Joi.object({
    name: Joi.string().optional(),
    address: Joi.string().optional(),
    contactEmail: Joi.string().email().optional(),
    contactPhone: Joi.string().optional(),
    settings: Joi.object().optional()
  }),

  // School schemas
  createSchool: Joi.object({
    name: Joi.string().required(),
    address: Joi.string().required(),
    lat: Joi.number().min(-90).max(90).required(),
    lng: Joi.number().min(-180).max(180).required(),
    startTime: Joi.string().pattern(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/).required(),
    endTime: Joi.string().pattern(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/).required(),
    principalName: Joi.string().optional(),
    contactEmail: Joi.string().email().optional(),
    contactPhone: Joi.string().optional()
  }),

  // Student schemas
  createStudent: Joi.object({
    schoolId: Joi.string().uuid().required(),
    firstName: Joi.string().required(),
    lastName: Joi.string().required(),
    grade: Joi.string().required(),
    address: Joi.string().required(),
    lat: Joi.number().min(-90).max(90).required(),
    lng: Joi.number().min(-180).max(180).required(),
    parentName: Joi.string().optional(),
    parentEmail: Joi.string().email().optional(),
    parentPhone: Joi.string().optional(),
    hasSpecialNeeds: Joi.boolean().default(false),
    specialNeedsInfo: Joi.string().optional(),
    photoUrl: Joi.string().uri().optional()
  }),

  // Bus schemas
  createBus: Joi.object({
    vehicleNumber: Joi.string().required(),
    capacity: Joi.number().min(1).required(),
    make: Joi.string().optional(),
    model: Joi.string().optional(),
    year: Joi.number().min(1900).max(new Date().getFullYear() + 1).optional(),
    licensePlate: Joi.string().optional(),
    hasWheelchairLift: Joi.boolean().default(false),
    hasAirConditioning: Joi.boolean().default(false),
    features: Joi.array().items(Joi.string()).optional()
  }),

  // Driver schemas
  createDriver: Joi.object({
    firstName: Joi.string().required(),
    lastName: Joi.string().required(),
    licenseNumber: Joi.string().required(),
    licenseExpiryDate: Joi.date().greater('now').required(),
    email: Joi.string().email().optional(),
    phone: Joi.string().required(),
    emergencyContact: Joi.string().optional(),
    emergencyPhone: Joi.string().optional(),
    address: Joi.string().optional(),
    hasCommercialLicense: Joi.boolean().default(false),
    hasPassedBackgroundCheck: Joi.boolean().default(false),
    hasPassedDrugTest: Joi.boolean().default(false)
  }),

  // Route optimization schemas
  optimizeRoutes: Joi.object({
    schoolIds: Joi.array().items(Joi.string().uuid()).optional(),
    routeType: Joi.string().valid('morning', 'afternoon', 'both').required(),
    constraints: Joi.object({
      maxRouteTime: Joi.number().min(30).max(120).optional(),
      maxWalkDistance: Joi.number().min(0).max(1).optional(),
      earliestPickupTime: Joi.string().pattern(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/).optional(),
      optimizeFor: Joi.string().valid('distance', 'time', 'balanced').default('balanced')
    }).optional()
  }),

  // GPS tracking schemas
  updateLocation: Joi.object({
    lat: Joi.number().min(-90).max(90).required(),
    lng: Joi.number().min(-180).max(180).required(),
    speed: Joi.number().min(0).optional(),
    heading: Joi.number().min(0).max(360).optional(),
    altitude: Joi.number().optional(),
    accuracy: Joi.number().optional(),
    timestamp: Joi.date().optional()
  }),

  // Common schemas
  pagination: Joi.object({
    page: Joi.number().min(1).default(1),
    limit: Joi.number().min(1).max(100).default(20),
    sortBy: Joi.string().optional(),
    sortOrder: Joi.string().valid('ASC', 'DESC').default('ASC')
  }),

  dateRange: Joi.object({
    startDate: Joi.date().required(),
    endDate: Joi.date().greater(Joi.ref('startDate')).required()
  })
};