import { Sequelize } from 'sequelize-typescript';
import { logger } from '../utils/logger';
import path from 'path';

const env = process.env.NODE_ENV || 'development';

const config = {
  database: process.env.DB_NAME || 'school_bus_optimizer',
  username: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'password',
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  dialect: 'postgres' as const,
  logging: env === 'development' ? (msg: string) => logger.debug(msg) : false,
  pool: {
    max: 10,
    min: 0,
    acquire: 30000,
    idle: 10000
  },
  define: {
    timestamps: true,
    underscored: true,
    freezeTableName: true
  }
};

export const sequelize = new Sequelize({
  ...config,
  models: [path.join(__dirname, '..', 'models')]
});

// Enable PostGIS extension
export const enablePostGIS = async () => {
  try {
    await sequelize.query('CREATE EXTENSION IF NOT EXISTS postgis;');
    logger.info('PostGIS extension enabled');
  } catch (error) {
    logger.error('Failed to enable PostGIS extension:', error);
    throw error;
  }
};