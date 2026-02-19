import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
  Default,
  HasMany,
  CreatedAt,
  UpdatedAt
} from 'sequelize-typescript';
import { School } from './School';
import { User } from './User';
import { Bus } from './Bus';
import { Driver } from './Driver';
import { Route } from './Route';

export interface DistrictSettings {
  maxRouteTime: number;
  maxWalkDistance: number;
  defaultPickupBuffer: number;
  notificationSettings: {
    smsEnabled: boolean;
    emailEnabled: boolean;
    pushEnabled: boolean;
  };
  routeOptimizationSettings: {
    algorithm: 'nearest-neighbor' | 'genetic' | 'simulated-annealing';
    optimizeFor: 'distance' | 'time' | 'balanced';
  };
}

@Table({
  tableName: 'districts',
  timestamps: true
})
export class District extends Model {
  @PrimaryKey
  @Default(DataType.UUIDV4)
  @Column(DataType.UUID)
  id!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false,
    unique: true
  })
  name!: string;

  @Column({
    type: DataType.STRING,
    allowNull: false
  })
  address!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  contactEmail!: string;

  @Column({
    type: DataType.STRING,
    allowNull: true
  })
  contactPhone!: string;

  @Column({
    type: DataType.ENUM('trial', 'basic', 'professional', 'enterprise'),
    defaultValue: 'trial'
  })
  subscriptionTier!: string;

  @Column({
    type: DataType.DATE,
    allowNull: true
  })
  subscriptionExpiresAt!: Date;

  @Column({
    type: DataType.JSON,
    defaultValue: {
      maxRouteTime: 60,
      maxWalkDistance: 0.5,
      defaultPickupBuffer: 5,
      notificationSettings: {
        smsEnabled: true,
        emailEnabled: true,
        pushEnabled: true
      },
      routeOptimizationSettings: {
        algorithm: 'nearest-neighbor',
        optimizeFor: 'balanced'
      }
    }
  })
  settings!: DistrictSettings;

  @Column({
    type: DataType.BOOLEAN,
    defaultValue: true
  })
  active!: boolean;

  @CreatedAt
  createdAt!: Date;

  @UpdatedAt
  updatedAt!: Date;

  // Associations
  @HasMany(() => School)
  schools!: School[];

  @HasMany(() => User)
  users!: User[];

  @HasMany(() => Bus)
  buses!: Bus[];

  @HasMany(() => Driver)
  drivers!: Driver[];

  @HasMany(() => Route)
  routes!: Route[];
}